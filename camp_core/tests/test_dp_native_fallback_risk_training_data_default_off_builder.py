from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner import atom_schema_for_dimension
from scripts.integrations.build_diffusion_planner_dp_native_fallback_risk_training_data import (
    COMPLETE_STATUS,
    DATASET_SCHEMA_VERSION,
    DISABLED_STATUS,
    REJECT_STATUS,
    build_training_data_report,
    main,
)
from scripts.integrations.validate_dp_native_training_data_contract import (
    CANDIDATE_GENERATION_SCHEMA_VERSION,
    PROVENANCE_SCHEMA_VERSION,
)


def _reward(
    *,
    red_light: object = -1.0,
    lane_crossing: object = False,
    centerline: object = 0.0,
    total: object = -50.0,
) -> dict[str, object]:
    return {
        "red_light": red_light,
        "lane_crossing": lane_crossing,
        "static_crossing": False,
        "off_road_fraction": 0.0,
        "lane_near_frac": 0.0,
        "lane_wide_frac": 0.0,
        "centerline": centerline,
        "total": total,
    }


def _provenance(
    *,
    candidate_count: int,
    selected_index: int,
    **overrides: object,
) -> dict[str, object]:
    tensor = {
        "sha256": "a" * 64,
        "shape": [candidate_count, 80, 4],
        "dtype": "float32",
        "hash_input": "contiguous_candidate_tensor_bytes",
        "nan_policy": "preserve_tensor_bytes",
    }
    payload: dict[str, object] = {
        "schema_version": PROVENANCE_SCHEMA_VERSION,
        "payload_valid": True,
        "candidate_count": candidate_count,
        "post_selector_candidate_count": candidate_count,
        "selected_index": selected_index,
        "selected_index_in_range": True,
        "pre_post_tensor_hash_equal": True,
        "no_candidate_row_append": True,
        "no_coordinate_heading_speed_rewrite_by_camp": True,
        "selection_effect": False,
        "candidate_generation_effect": False,
        "candidate_tensor_mutation_effect": False,
        "candidate_generation_authorized": False,
        "trajectory_rewrite_authorized": False,
        "dp_modification_authorized": False,
        "outcome_label_input": False,
        "closed_loop_outcome_fields_read": False,
        "pre_camp_scoring_tensor": tensor,
        "post_camp_selector_tensor": tensor,
    }
    payload.update(overrides)
    return payload


def _record(
    *,
    reasons: list[list[str]] | None = None,
    rewards: list[dict[str, object]] | None = None,
    feasible_mask: list[bool] | None = None,
    atoms: list[list[float]] | None = None,
    selected_index: int = 0,
    provenance_overrides: dict[str, object] | None = None,
    generation_overrides: dict[str, object] | None = None,
) -> dict[str, object]:
    rewards = rewards or [_reward(), _reward(red_light=-2.0)]
    candidate_count = len(rewards)
    version, names = atom_schema_for_dimension(9)
    atoms = atoms or [[0.1 * (index + 1) for _ in range(9)] for index in range(candidate_count)]
    generation: dict[str, object] = {
        "schema_version": CANDIDATE_GENERATION_SCHEMA_VERSION,
        "num_candidates": candidate_count,
        "noise_strategy": "iid",
        "reference_blend_steps": None,
        "guidance_enabled": False,
        "changes_diffusion_planner_weights": False,
    }
    generation.update(generation_overrides or {})
    return {
        "selection_step": 0,
        "selected_index": selected_index,
        "num_candidates": candidate_count,
        "feasible_mask": feasible_mask or [False for _ in range(candidate_count)],
        "infeasibility_reasons": reasons
        or [["dp_red_light"] for _ in range(candidate_count)],
        "dp_candidate_rewards": rewards,
        "atom_schema_version": version,
        "atom_names": list(names),
        "atoms": atoms,
        "normalized_atoms": atoms,
        "candidate_generation_contract": generation,
        "camp_candidate_tensor_provenance": _provenance(
            candidate_count=candidate_count,
            selected_index=selected_index,
            **(provenance_overrides or {}),
        ),
    }


def _write_log(tmp_path: Path, records: list[dict[str, object]]) -> Path:
    log_path = tmp_path / "camp_selection_log.json"
    log_path.write_text(json.dumps(records), encoding="utf-8")
    return log_path


def _record_identity_hash(record: dict[str, object]) -> str:
    identity = {
        "source_log": record.get("source_log"),
        "source_log_sha256": record.get("source_log_sha256"),
        "run_id": record.get("run_id"),
        "record_index": record.get("record_index"),
    }
    return hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def test_builder_is_default_off_and_does_not_read_missing_log(tmp_path: Path) -> None:
    report = build_training_data_report(
        selection_logs=[tmp_path / "missing.json"],
        enabled=False,
    )

    assert report["schema_version"] == DATASET_SCHEMA_VERSION
    assert report["records"] == []
    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["final_decision"]["passed"] is True


def test_builder_enabled_builds_all_infeasible_records_and_skips_feasible(
    tmp_path: Path,
) -> None:
    log_path = _write_log(
        tmp_path,
        [
            _record(
                reasons=[["dp_red_light"], ["dp_red_light"]],
                rewards=[_reward(red_light=-3.0), _reward(red_light=-1.0)],
            ),
            _record(feasible_mask=[True, False]),
        ],
    )

    report = build_training_data_report(selection_logs=[log_path], enabled=True)
    built = report["records"][0]

    assert report["final_decision"]["status"] == COMPLETE_STATUS
    assert report["record_counts"]["records_total"] == 2
    assert report["record_counts"]["records_with_feasible_candidate"] == 1
    assert report["record_counts"]["records_without_feasible_candidate"] == 1
    assert report["record_counts"]["records_built"] == 1
    assert built["record_identity_hash"] == _record_identity_hash(built)
    assert built["oracle_index"] == 1
    assert built["oracle_policy"] == ["red", "lane", "quality"]
    assert built["training_authorized"] is False


def test_builder_reason_conditioned_label_policy(tmp_path: Path) -> None:
    log_path = _write_log(
        tmp_path,
        [
            _record(
                reasons=[["dp_lane_crossing"], ["dp_lane_crossing"]],
                rewards=[
                    _reward(lane_crossing=True, red_light=-1.0),
                    _reward(lane_crossing=False, red_light=-5.0),
                ],
            ),
            _record(
                reasons=[["dp_other"], ["dp_other"]],
                rewards=[_reward(total=-9.0), _reward(total=-1.0)],
            ),
        ],
    )

    report = build_training_data_report(selection_logs=[log_path], enabled=True)

    assert report["final_decision"]["status"] == COMPLETE_STATUS
    assert report["records"][0]["oracle_policy"] == ["lane", "red", "quality"]
    assert report["records"][0]["oracle_index"] == 1
    assert report["records"][1]["oracle_policy"] == ["quality", "red", "lane"]
    assert report["records"][1]["oracle_index"] == 1
    assert all(value >= 0.0 for value in report["records"][0]["margins"])


def test_builder_fails_closed_on_bad_fields(tmp_path: Path) -> None:
    bad_reward = _reward(red_light="bad")
    del bad_reward["centerline"]
    log_path = _write_log(
        tmp_path,
        [
            _record(
                rewards=[bad_reward, _reward()],
                atoms=[[-0.1 for _ in range(9)], [0.1 for _ in range(9)]],
                provenance_overrides={"pre_post_tensor_hash_equal": False},
                generation_overrides={"guidance_enabled": True},
            )
        ],
    )

    report = build_training_data_report(selection_logs=[log_path], enabled=True)
    errors = report["final_decision"]["errors"]

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert any("reward_0_missing_fields:centerline" in item for item in errors)
    assert any("provenance_pre_post_tensor_hash_equal_not_true" in item for item in errors)
    assert any("candidate_generation_contract_guidance_enabled" in item for item in errors)
    assert any("atoms_0_not_finite_nonnegative" in item for item in errors)
    assert report["final_decision"]["camp_training_authorized"] is False
    assert report["final_decision"]["dp_modification_authorized"] is False


def test_builder_fails_closed_on_loose_types_and_atom_shape_mismatch(
    tmp_path: Path,
) -> None:
    bad = _record(
        feasible_mask=["false", False],
        atoms=[[0.1 for _ in range(9)], [0.1 for _ in range(8)]],
        generation_overrides={"num_candidates": "2"},
    )
    bad["selected_index"] = True
    bad["camp_candidate_tensor_provenance"]["candidate_count"] = "2"
    bad["camp_candidate_tensor_provenance"]["selected_index"] = True
    bad["normalized_atoms"] = [[-0.1 for _ in range(9)], [0.1 for _ in range(9)]]
    log_path = _write_log(tmp_path, [bad])

    report = build_training_data_report(selection_logs=[log_path], enabled=True)
    errors = report["final_decision"]["errors"]

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert any("feasible_mask_invalid" in item for item in errors)

    bad["feasible_mask"] = [False, False]
    log_path = _write_log(tmp_path, [bad])
    report = build_training_data_report(selection_logs=[log_path], enabled=True)
    errors = report["final_decision"]["errors"]

    assert report["final_decision"]["status"] == REJECT_STATUS
    for needle in [
        "selected_index_not_int",
        "candidate_generation_contract_num_candidates_not_int",
        "provenance_candidate_count_not_int",
        "atoms_1_row_dimension_mismatch",
        "normalized_atoms_0_not_finite_nonnegative",
    ]:
        assert any(needle in item for item in errors)


def test_builder_cli_writes_reports_when_enabled(tmp_path: Path) -> None:
    log_path = _write_log(tmp_path, [_record()])
    output_json = tmp_path / "out" / "dataset.json"
    output_md = tmp_path / "out" / "dataset.md"

    exit_code = main(
        [
            "--selection_log",
            str(log_path),
            "--enable_default_off_fallback_risk_training_data_builder",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ]
    )

    report = json.loads(output_json.read_text(encoding="utf-8"))
    markdown = output_md.read_text(encoding="utf-8")
    assert exit_code == 0
    assert report["final_decision"]["status"] == COMPLETE_STATUS
    assert "training_authorized=False" in markdown
