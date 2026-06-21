from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_red_route_vector_logging import (
    AUTHORIZED_NEXT_WORK,
    FIELD_SPECS,
    READY_STATUS,
    REJECT_STATUS,
    RedVectorFieldSpec,
    build_report,
)


def _semantics_source(
    *,
    status: str = "red_alignment_sign_semantics_underdetermined",
    passed: bool = True,
    next_work: str = (
        "predeclare_red_route_point_vector_logging_plan_or_reject_red_descriptor"
    ),
    current_support: int = 0,
    reverse_support: int = 2,
    within_budget: int = 2,
    geometry_records: int = 0,
    geometry_fields: dict | None = None,
) -> dict:
    return {
        "counts": {
            "within_budget_candidate_count": within_budget,
            "current_mean_supported_candidate_count": current_support,
            "reverse_mean_supported_candidate_count": reverse_support,
            "records_with_logged_red_geometry": geometry_records,
        },
        "geometry_fields": {} if geometry_fields is None else geometry_fields,
        "final_decision": {
            "status": status,
            "passed": passed,
            "authorized_next_work": next_work,
        },
    }


def _replay_script(tmp_path: Path, *, include_tokens: bool = True) -> Path:
    path = tmp_path / "run_diffusion_planner_camp_replay.py"
    if include_tokens:
        path.write_text(
            "\n".join(
                [
                    "OBSERVABLE_STATE_FIELDS = ()",
                    "def _candidate_red_light_relation(): pass",
                    "def _observable_state_logging_payload(): pass",
                    "red_route_points_from_scene(scene, ego_id)",
                    "candidate_red_stopline_distance_m",
                    "candidate_red_heading_alignment",
                    '"default_off": True',
                    '"selection_effect": False',
                    '"future_outcome_leakage": False',
                ]
            ),
            encoding="utf-8",
        )
    else:
        path.write_text("def placeholder(): pass\n", encoding="utf-8")
    return path


def test_red_route_vector_logging_plan_authorizes_unit_implementation_only(
    tmp_path: Path,
) -> None:
    report = build_report(
        red_semantics_report=_semantics_source(),
        replay_script=_replay_script(tmp_path),
        label="unit",
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert report["final_decision"]["implementation_authorized"] is True
    assert report["final_decision"]["new_replay_authorized"] is False
    assert report["final_decision"]["offline_separability_authorized"] is False
    assert report["final_decision"]["formal_seeds_authorized"] is False
    assert report["final_decision"]["CAMP_retraining_authorized"] is False
    assert report["final_decision"]["classic_Benders_claim_authorized"] is False
    assert report["analysis"]["closed_loop_outcome_labels_used"] is False
    assert report["analysis"]["online_selector_change"] is False

    field_names = {field["name"] for field in report["field_specs"]}
    assert "red_route_points_ego_xy_dir" in field_names
    assert "candidate_red_selected_route_point_index" in field_names
    assert "candidate_red_heading_vector_xy" in field_names
    assert "candidate_red_alignment_recomputed_reverse" in field_names


def test_red_route_vector_logging_plan_rejects_invalid_source(tmp_path: Path) -> None:
    report = build_report(
        red_semantics_report=_semantics_source(
            status="red_alignment_current_payload_rejected",
            passed=True,
            next_work="reject_current_red_alignment_descriptor_for_existing_payloads",
        ),
        replay_script=_replay_script(tmp_path),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == ["red_semantics_gate_authorizes_vector_plan"]


def test_red_route_vector_logging_plan_requires_missing_geometry_gap(
    tmp_path: Path,
) -> None:
    report = build_report(
        red_semantics_report=_semantics_source(
            geometry_records=2,
            geometry_fields={"red_route_points": 2},
        ),
        replay_script=_replay_script(tmp_path),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["source_checks"] if not check["passed"]]
    assert failed == ["source_geometry_missing_so_plan_is_needed"]


def test_red_route_vector_logging_plan_rejects_field_with_selection_effect(
    tmp_path: Path,
) -> None:
    bad_specs = (
        replace(FIELD_SPECS[0], selection_effect=True),
        *FIELD_SPECS[1:],
    )
    report = build_report(
        red_semantics_report=_semantics_source(),
        replay_script=_replay_script(tmp_path),
        field_specs=bad_specs,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["field_checks"] if not check["passed"]]
    assert failed == ["fields_are_default_off_and_selector_neutral"]


def test_red_route_vector_logging_plan_rejects_missing_required_field(
    tmp_path: Path,
) -> None:
    reduced = tuple(
        spec
        for spec in FIELD_SPECS
        if spec.name != "candidate_red_heading_vector_xy"
    )
    report = build_report(
        red_semantics_report=_semantics_source(),
        replay_script=_replay_script(tmp_path),
        field_specs=reduced,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    required_check = next(
        check for check in report["field_checks"] if check["name"] == "required_fields_present"
    )
    assert required_check["missing"] == ["candidate_red_heading_vector_xy"]


def test_red_route_vector_logging_plan_rejects_missing_replay_hooks(
    tmp_path: Path,
) -> None:
    report = build_report(
        red_semantics_report=_semantics_source(),
        replay_script=_replay_script(tmp_path, include_tokens=False),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    failed = [check["name"] for check in report["hook_checks"] if not check["passed"]]
    assert failed == [
        "existing_red_relation_hooks_available",
        "existing_observable_logging_is_default_off",
    ]


def test_red_route_vector_logging_field_specs_do_not_claim_atoms() -> None:
    assert all(isinstance(spec, RedVectorFieldSpec) for spec in FIELD_SPECS)
    assert not any(spec.atom_candidate for spec in FIELD_SPECS)
    assert all(spec.default_off for spec in FIELD_SPECS)
    assert not any(spec.future_outcome_leakage for spec in FIELD_SPECS)
