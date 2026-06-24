from __future__ import annotations

import json
from pathlib import Path

from camp_core.integrations.diffusion_planner import atom_schema_for_dimension
from scripts.integrations.validate_dp_native_training_data_contract import (
    PROVENANCE_SCHEMA_VERSION,
)
from scripts.integrations.validate_dp_native_training_sufficiency_preflight import (
    evaluate_training_sufficiency,
    main,
)


def _sha(value: str) -> str:
    return value * 64


def _record(*, selected_index: int = 0, include_dp_rewards: bool = True) -> dict:
    version, names = atom_schema_for_dimension(9)
    record = {
        "selected_index": selected_index,
        "atom_schema_version": version,
        "atom_names": list(names),
        "atoms": [
            [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9],
            [0.2, 0.1, 0.4, 0.3, 0.6, 0.5, 0.8, 0.7, 1.0],
        ],
        "feasible_mask": [True, True],
        "candidate_generation_contract": {
            "schema_version": "dp_candidate_generation_contract_v1",
            "num_candidates": 2,
            "noise_strategy": "iid",
            "reference_blend_steps": None,
            "guidance_enabled": False,
            "changes_diffusion_planner_weights": False,
        },
        "camp_candidate_tensor_provenance": {
            "schema_version": PROVENANCE_SCHEMA_VERSION,
            "selection_effect": False,
            "candidate_generation_effect": False,
            "candidate_tensor_mutation_effect": False,
            "candidate_generation_authorized": False,
            "trajectory_rewrite_authorized": False,
            "dp_modification_authorized": False,
            "payload_valid": True,
            "pre_post_tensor_hash_equal": True,
            "selected_index_in_range": True,
            "no_candidate_row_append": True,
            "no_coordinate_heading_speed_rewrite_by_camp": True,
            "reference_blend_stage_hash_separated": True,
            "outcome_label_input": False,
            "closed_loop_outcome_fields_read": False,
            "candidate_count": 2,
            "post_selector_candidate_count": 2,
            "selected_index": selected_index,
            "pre_camp_scoring_tensor": {
                "sha256": _sha("a"),
                "shape": [2, 80, 4],
                "dtype": "float32",
                "hash_input": "contiguous_candidate_tensor_bytes",
                "nan_policy": "preserve_tensor_bytes",
            },
            "post_camp_selector_tensor": {
                "sha256": _sha("a"),
                "shape": [2, 80, 4],
                "dtype": "float32",
                "hash_input": "contiguous_candidate_tensor_bytes",
                "nan_policy": "preserve_tensor_bytes",
            },
        },
    }
    if include_dp_rewards:
        record["dp_candidate_rewards"] = [
            {"total": 2.0, "progress": 0.5},
            {"total": 1.0, "progress": 0.1},
        ]
    return record


def _write_log(root: Path, name: str, records: list[dict]) -> Path:
    path = root / name / "camp_selection_log.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


def test_current_scale_artifact_shape_fails_development_profile(tmp_path: Path) -> None:
    paths = [
        _write_log(tmp_path, "sample_tl_seed101_tl_on", [_record() for _ in range(3)]),
        _write_log(
            tmp_path, "sample_normal_seed102_tl_off", [_record() for _ in range(3)]
        ),
    ]

    report = evaluate_training_sufficiency(
        paths,
        label_source="dp_reward",
    )

    assert report["passed"] is False
    assert "records_at_least_min" in report["failed_checks"]
    assert "routes_at_least_min" in report["failed_checks"]
    assert "seeds_at_least_min" in report["failed_checks"]
    assert report["training_execution_authorized"] is False


def test_preflight_passes_when_explicit_thresholds_are_met(tmp_path: Path) -> None:
    paths = [
        _write_log(tmp_path, "sample_tl_seed101_tl_on", [_record()]),
        _write_log(tmp_path, "sample_normal_seed102_tl_off", [_record()]),
    ]

    report = evaluate_training_sufficiency(
        paths,
        label_source="dp_reward",
        min_records=2,
        min_routes=2,
        min_seeds=2,
        min_traffic_light_states=2,
        require_heldout_split=True,
    )

    assert report["passed"] is True
    assert report["routes"] == {"sample_normal": 1, "sample_tl": 1}
    assert report["seeds"] == {"101": 1, "102": 1}
    assert report["traffic_lights"] == {"off": 1, "on": 1}
    assert report["read_only"] is True


def test_preflight_rejects_missing_label_source_records(tmp_path: Path) -> None:
    path = _write_log(
        tmp_path,
        "sample_tl_seed101_tl_on",
        [_record(include_dp_rewards=False)],
    )

    report = evaluate_training_sufficiency(
        [path],
        label_source="dp_reward",
        min_records=1,
        min_routes=1,
        min_seeds=1,
        min_traffic_light_states=1,
    )

    assert report["passed"] is False
    assert "label_source_records_present" in report["failed_checks"]
    assert report["label_failed_records"][0]["errors"] == [
        "dp_candidate_rewards_missing"
    ]


def test_preflight_rejects_formal_seed_unless_explicitly_allowed(tmp_path: Path) -> None:
    path = _write_log(tmp_path, "sample_tl_seed11_tl_on", [_record()])

    blocked = evaluate_training_sufficiency(
        [path],
        label_source="dp_reward",
        min_records=1,
        min_routes=1,
        min_seeds=1,
        min_traffic_light_states=1,
    )
    allowed = evaluate_training_sufficiency(
        [path],
        label_source="dp_reward",
        min_records=1,
        min_routes=1,
        min_seeds=1,
        min_traffic_light_states=1,
        allow_formal_seeds=True,
    )

    assert blocked["passed"] is False
    assert "formal_seeds_absent_or_allowed" in blocked["failed_checks"]
    assert allowed["passed"] is True


def test_preflight_cli_writes_read_only_reports(tmp_path: Path, capsys) -> None:
    log_path = _write_log(tmp_path, "sample_tl_seed101_tl_on", [_record()])
    json_path = tmp_path / "report.json"
    md_path = tmp_path / "report.md"

    exit_code = main(
        [
            "--selection_log",
            str(log_path),
            "--label_source",
            "dp_reward",
            "--min_records",
            "1",
            "--min_routes",
            "1",
            "--min_seeds",
            "1",
            "--min_traffic_light_states",
            "1",
            "--output_json",
            str(json_path),
            "--output_md",
            str(md_path),
        ]
    )

    assert exit_code == 0
    report = json.loads(json_path.read_text(encoding="utf-8"))
    assert report["passed"] is True
    assert report["replay_executed"] is False
    assert report["candidate_generation_executed"] is False
    assert report["training_execution_authorized"] is False
    markdown = md_path.read_text(encoding="utf-8")
    assert "Training execution authorized: `False`" in markdown
    assert '"passed": true' in capsys.readouterr().out
