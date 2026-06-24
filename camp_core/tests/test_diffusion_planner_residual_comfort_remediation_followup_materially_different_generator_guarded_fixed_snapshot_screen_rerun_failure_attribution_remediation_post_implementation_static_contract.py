from __future__ import annotations

import importlib
from pathlib import Path


MODULE = (
    "scripts.integrations.review_diffusion_planner_residual_comfort_remediation_"
    "followup_materially_different_generator_guarded_fixed_snapshot_screen_"
    "rerun_failure_attribution_remediation_post_implementation_static_contract"
)
target = importlib.import_module(MODULE)

CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _audit_text() -> str:
    return f"""
## 2026-06-24 - Materially different generator failure-attribution remediation implementation only

Accept
`{target.IMPLEMENTATION_GATE}`
as complete.

candidate_generation_execution_authorized=False
fixed_snapshot_screen_rerun_authorized=False
new_replay_authorized=False
training_execution_authorized=False
atom_promotion_authorized=False
dp_modification_authorized=False

Next admissible gate:

`{target.CURRENT_GATE}`.
"""


def _source_text() -> str:
    return f'''
REMEDIATION_PROFILE_OFF = "off"
REMEDIATION_PROFILE_SUPPORT_V1 = "lane_projected_jerk_progress_support_v1"
REMEDIATION_PROFILE_MATERIAL_SUPPORT_V1 = "lane_station_jerk_limited_red_stop_support_v1"
REMEDIATION_PROFILE_MATERIAL_SUPPORT_V2 = "{target.MATERIAL_PROFILE_V2}"
GENERATOR_POLICY_MATERIAL_SUPPORT_V2 = "{target.MATERIAL_POLICY_V2}"
MATERIAL_SUPPORT_POLICY_PROFILES = {{
    GENERATOR_POLICY_MATERIAL_SUPPORT_V2: REMEDIATION_PROFILE_MATERIAL_SUPPORT_V2,
}}

class RouteTopologyCandidateConfig:
    generator_policy: str = "lane_centerline_red_stop"
    default_off_remediation_profile: str = REMEDIATION_PROFILE_OFF

def build_route_topology_candidates(raw, config):
    if _material_support_profile_failure(config) is not None:
        return np.empty((0, raw.shape[1], raw.shape[2]), dtype=np.float64), []
    if _is_material_support_v2_policy(config):
        continue
    row = {{
        "candidate0_preserved": True,
        "dp_rows_preserved": True,
        "append_after_existing_candidate_count": int(raw.shape[0]),
        "source_candidate_index": int(selected_index),
        "lane_red_hard_feasibility_precheck": True,
        "hard_feasibility_precheck_passed": True,
        "hard_progress_comfort_gate_passthrough": True,
        "lateral_heading_continuity_projection": True,
        "no_gate_relaxation": True,
    }}

def _lane_station_material_support_candidates(
    selected,
    *,
    lane,
    cumulative,
    current_s,
    stop_distances,
    offset_scales,
    prefix_steps,
    bridge_steps,
):
    selected_arr = np.asarray(selected)
    selected_s, selected_lateral = _project_points_to_lane(
        selected_arr[:, :2],
        lane,
        cumulative,
    )
    selected_forward = np.maximum(selected_s - float(current_s), 0.0)
    selected_forward = np.maximum.accumulate(selected_forward)
    target_forward = np.minimum(selected_forward, stop_distances)
    target_forward = np.maximum.accumulate(target_forward)
    lateral = np.nan_to_num(selected_lateral, nan=0.0, posinf=0.0, neginf=0.0)
    envelope[: int(prefix)] = 1.0
    envelope[step] = (1.0 - _smoothstep(u)) + _smoothstep(u) * offset_scale
    xy[: int(prefix)] = selected_arr[: int(prefix), :2]
    candidate[:, 2:4] = heading_features_from_xy(
        xy,
        fallback=selected_arr[:, 2:4],
    )
    return []

def _lane_red_hard_feasibility_precheck(*, stop_distance, red_distance, max_forward, current_speed_mps, config):
    margins = {{
        "red_ahead_margin_m": red_distance,
        "stop_distance_margin_m": stop_distance,
        "forward_range_margin_m": max_forward,
        "kinematic_deceleration_margin_mps2": current_speed_mps,
    }}
    failure_reason = "kinematic_deceleration_margin_negative"
    return {{"passed": True, "margins": margins, "uses_outcome_labels": False}}

def _command_jerk_descriptor_payload():
    return {{
        "score_contract": "score_k(w)=a_k^T w",
        "convex_master_contract": "simplex/CVaR/L2 unchanged",
        "current_tick_features_only": True,
        "candidate_local": True,
        "uses_outcome_labels": False,
        "future_outcome_leakage": False,
    }}

def _material_support_descriptor_payload(candidate, *, selected, lane, cumulative, current_s, dt, config, hard_precheck=None):
    payload = _command_jerk_descriptor_payload()
    payload.update({{
        "diagnostic_descriptor_payload_v2": True,
        "descriptor_family": "lane_red_hard_feasible_jerk_lateral_material_support",
        "hard_feasibility_margin_hinges": True,
        "hard_feasibility_red_ahead_margin_m": 1.0,
        "hard_feasibility_stop_distance_margin_m": 1.0,
        "hard_feasibility_forward_range_margin_m": 1.0,
        "hard_feasibility_kinematic_deceleration_margin_mps2": 1.0,
        "current_tick_features_only": True,
        "candidate_local": True,
        "uses_outcome_labels": False,
        "future_outcome_leakage": False,
        "runtime_atom_promotion": False,
        "nonnegative_descriptor_channels": True,
        "hinge_signed_split_channels": True,
        "affine_score_compatible": True,
        "score_contract": "score_k(w)=a_k^T w",
        "convex_master_contract": "simplex/CVaR/L2 unchanged",
    }})
    return payload

def _effective_comfort_budgets(config):
    if config.default_off_remediation_profile not in {{
        REMEDIATION_PROFILE_SUPPORT_V1,
        REMEDIATION_PROFILE_MATERIAL_SUPPORT_V1,
        REMEDIATION_PROFILE_MATERIAL_SUPPORT_V2,
    }}:
        return {{}}
    return {{
        "progress_loss_budgets_m": _budgets_with_floor((0.5,), 2.0),
        "command_jerk_worse_budget_mps3": 0.05,
        "rollout_lateral_worse_budget_mps2": 1.0,
    }}

def _material_support_profile_failure(config):
    required_profile = MATERIAL_SUPPORT_POLICY_PROFILES.get(config.generator_policy)
    if required_profile is not None:
        return "material_support_profile_required"
    return "material_support_policy_required"

def _validate_config(config):
    if _material_support_profile_failure(config) is not None:
        raise ValueError(_material_support_profile_failure(config))
'''


def _route_test_text() -> str:
    return """
def test_route_topology_generator_builds_default_off_jerk_progress_policy(): pass
def test_route_topology_generator_builds_negative_support_followup_policy(): pass
def test_route_topology_report_rejects_invalid_remediation_candidate_cap():
    assert "max_remediation_candidates must be positive"
"""


def _contract_test_text() -> str:
    return """
def test_v2_default_off_and_v1_behavior_unchanged(): pass
def test_v2_requires_explicit_policy_profile_pair(): pass
def test_v2_preserves_candidate0_and_dp_rows_while_appending_support(): pass
def test_v2_hard_precheck_fails_closed_on_kinematic_margin(): pass
def test_v2_rejects_nonfinite_current_tick_inputs(): pass
def test_v2_descriptor_legality_and_affine_contract(): pass
assert "candidate0_preserved"
assert "dp_rows_preserved"
assert "lane_red_hard_feasibility_precheck"
assert "hard_feasibility_precheck_passed"
assert "no_gate_relaxation"
assert "diagnostic_descriptor_payload_v2"
assert "current_tick_features_only"
assert "uses_outcome_labels"
assert "future_outcome_leakage"
assert "hard_feasibility_margin_hinges"
assert "nonnegative_descriptor_channels"
assert "hinge_signed_split_channels"
assert "affine_score_compatible"
assert "score_k(w)=a_k^T w"
assert "simplex/CVaR/L2 unchanged"
assert "online_selector_feature"
assert "deployed_atom_schema_change"
"""


def _write_inputs(
    tmp_path: Path,
    *,
    audit_text: str | None = None,
    source_text: str | None = None,
    route_test_text: str | None = None,
    contract_test_text: str | None = None,
) -> tuple[Path, Path, Path, Path]:
    audit = tmp_path / "audit.md"
    source = tmp_path / "source.py"
    route_test = tmp_path / "test_route.py"
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


def test_remediation_post_implementation_static_contract_review_ready(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    review = report["post_implementation_static_contract_review"]

    assert decision["status"] == target.READY_STATUS
    assert decision["passed"] is True
    assert decision["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert review["source_contract"]["contracts"][
        "v2_hard_precheck_fail_closed_without_gate_relaxation"
    ] is True
    assert review["contract_test_contract"]["contracts"][
        "v2_implementation_tests_present"
    ] is True


def test_remediation_post_review_rejects_bad_dp_head(tmp_path: Path) -> None:
    report = _build(tmp_path, dp_head="bad")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_remediation_post_review_requires_current_gate_in_audit(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_text=_audit_text().replace(target.CURRENT_GATE, "bad"))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "audit_authorizes_current_gate" in report["final_decision"]["failed_checks"]


def test_remediation_post_review_rejects_missing_v2_descriptor_token(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        source_text=_source_text().replace("diagnostic_descriptor_payload_v2", "missing"),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert (
        "source_contract.descriptor_v2_legality_report_only"
        in report["final_decision"]["failed_checks"]
    )


def test_remediation_post_review_markdown_renders(tmp_path: Path) -> None:
    report = _build(tmp_path)
    md = target.render_markdown(report)

    assert "Material Generator Remediation Post-Implementation" in md
    assert target.AUTHORIZED_NEXT_WORK in md
    assert "Math Boundary" in md
