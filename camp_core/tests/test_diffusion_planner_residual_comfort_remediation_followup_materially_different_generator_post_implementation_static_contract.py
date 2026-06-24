from __future__ import annotations

import importlib
import json
from pathlib import Path


MODULE = (
    "scripts.integrations.review_diffusion_planner_residual_comfort_remediation_"
    "followup_materially_different_generator_post_implementation_static_contract"
)
target = importlib.import_module(MODULE)

CAMP_COMMIT = "bff8f8bf99a6b90a3ab5190b0d83b47eb1ed686a"


def _audit_text() -> str:
    return f"""
## 2026-06-24 - Materially different generator implementation only

Accept
`{target.IMPLEMENTATION_GATE}`
as complete.

This gate implemented the reviewed default-off materially different generator
path and focused implementation contracts only. It did not execute candidate
generation, execute another fixed-snapshot screen rerun, run replay, use formal
seeds, expand to Full36, train CAMP, promote atoms, change the online selector,
claim safety benefit, claim CAMP is better than DP Top-1, or modify DP.

Next admissible gate:

`{target.CURRENT_GATE}`.
"""


def _source_text() -> str:
    return f'''
REMEDIATION_PROFILE_OFF = "off"
REMEDIATION_PROFILE_SUPPORT_V1 = "lane_projected_jerk_progress_support_v1"
REMEDIATION_PROFILE_MATERIAL_SUPPORT_V1 = "{target.MATERIAL_PROFILE}"
GENERATOR_POLICY_MATERIAL_SUPPORT = "{target.MATERIAL_POLICY}"

class RouteTopologyCandidateConfig:
    generator_policy: str = "lane_centerline_red_stop"
    default_off_remediation_profile: str = REMEDIATION_PROFILE_OFF

def parse_args():
    parser.add_argument(
        "--generator_policy",
        choices=("lane_centerline_red_stop", GENERATOR_POLICY_MATERIAL_SUPPORT),
        default="lane_centerline_red_stop",
    )
    parser.add_argument(
        "--default_off_remediation_profile",
        choices=(
            REMEDIATION_PROFILE_OFF,
            REMEDIATION_PROFILE_SUPPORT_V1,
            REMEDIATION_PROFILE_MATERIAL_SUPPORT_V1,
        ),
        default=REMEDIATION_PROFILE_OFF,
    )

def build_route_topology_candidates(raw, config):
    if _material_support_profile_failure(config) is not None:
        return np.empty((0, raw.shape[1], raw.shape[2]), dtype=np.float64), []
    if config.generator_policy == GENERATOR_POLICY_MATERIAL_SUPPORT:
        metadata.append({{
            "candidate0_preserved": True,
            "dp_rows_preserved": True,
            "append_after_existing_candidate_count": int(raw.shape[0]),
            "source_candidate_index": int(selected_index),
            "hard_progress_comfort_gate_passthrough": True,
            "red_timing_progress_guard": True,
            "remediation_descriptor_payload": _material_support_descriptor_payload(
                candidate,
                selected=raw[selected_index],
                lane=lane,
                cumulative=cumulative,
                current_s=current_s,
                dt=dt,
                config=config,
            ),
        }})
    _comfort_admissible(row, config=config)
    route_failure_classes(row, config=config)

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

def _command_jerk_descriptor_payload():
    return {{
        "score_contract": "score_k(w)=a_k^T w",
        "convex_master_contract": "simplex/CVaR/L2 unchanged",
    }}

def _material_support_descriptor_payload(candidate, *, selected, lane, cumulative, current_s, dt, config):
    payload = _command_jerk_descriptor_payload()
    payload.update({{
        "descriptor_family": "lane_station_jerk_limited_red_stop_material_support",
        "material_descriptor_family": "command_rollout_jerk_lateral_progress_lane_projection",
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
    }}:
        return {{}}
    return {{
        "progress_loss_budgets_m": _budgets_with_floor((0.5,), 2.0),
        "command_jerk_worse_budget_mps3": 0.05,
        "rollout_lateral_worse_budget_mps2": 1.0,
    }}

def _material_support_profile_failure(config):
    if config.generator_policy == GENERATOR_POLICY_MATERIAL_SUPPORT:
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
def test_material_generator_default_config_remains_default_off(): pass
def test_material_generator_requires_explicit_policy_profile_pair(): pass
def test_material_generator_builds_candidate0_preserving_support_rows(): pass
def test_material_generator_descriptor_payload_is_report_only_and_nonnegative(): pass
def test_material_generator_fails_closed_on_nonfinite_current_tick_inputs(): pass
def test_material_generator_candidate_budget_cap_is_deterministic(): pass
def test_material_generator_validate_config_rejects_profile_policy_mismatch(): pass
def test_material_generator_effective_budgets_match_reviewed_support_floor(): pass
assert "candidate0_preserved"
assert "dp_rows_preserved"
assert "current_tick_features_only"
assert "uses_outcome_labels"
assert "future_outcome_leakage"
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


def test_material_post_implementation_static_contract_review_ready(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    review = report["post_implementation_static_contract_review"]

    assert decision["status"] == target.READY_STATUS
    assert decision["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert decision["post_implementation_static_contract_review_complete"] is True
    assert decision["fixed_snapshot_screen_rerun_plan_authorized"] is True
    assert decision["implementation_code_edit_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert all(review["source_contract"]["contracts"].values())
    assert all(review["contract_test_contract"]["contracts"].values())


def test_material_post_implementation_static_contract_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]
    assert report["final_decision"]["authorized_next_work"] is None


def test_material_post_implementation_static_contract_rejects_missing_audit_gate(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, audit_text="not authorized")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "audit_records_implementation_gate" in report["final_decision"][
        "failed_checks"
    ]
    assert "audit_authorizes_current_gate" in report["final_decision"][
        "failed_checks"
    ]


def test_material_post_implementation_static_contract_rejects_default_on_drift(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        source_text=_source_text().replace(
            'default_off_remediation_profile: str = REMEDIATION_PROFILE_OFF',
            'default_off_remediation_profile: str = REMEDIATION_PROFILE_MATERIAL_SUPPORT_V1',
        ),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "source_contract_default_off_opt_in_pairing" in report["final_decision"][
        "failed_checks"
    ]


def test_material_post_implementation_static_contract_rejects_profile_pair_gap(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        source_text=_source_text().replace(
            "raise ValueError(_material_support_profile_failure(config))",
            "return None",
        ),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "source_contract_profile_policy_mismatch_fails_closed" in report[
        "final_decision"
    ]["failed_checks"]


def test_material_post_implementation_static_contract_rejects_descriptor_drift(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        source_text=_source_text().replace('"affine_score_compatible": True,', ""),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "source_contract_descriptor_legality_report_only" in report[
        "final_decision"
    ]["failed_checks"]


def test_material_post_implementation_static_contract_rejects_missing_contract_test(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        contract_test_text=_contract_test_text().replace(
            "test_material_generator_fails_closed_on_nonfinite_current_tick_inputs",
            "test_missing_current_tick_check",
        ),
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "contract_test_contract_material_implementation_tests_present" in report[
        "final_decision"
    ]["failed_checks"]


def test_material_post_implementation_static_contract_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    audit, source, route_test, contract_test = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "review.json"
    output_md = tmp_path / "out" / "review.md"
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
    assert report["final_decision"]["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert "Post-Implementation Static Contract Review" in markdown
    assert "candidate generation execution is not authorized" in markdown
    assert "formal seeds 11/12/13 remain frozen" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "simplex/CVaR/L2" in markdown
