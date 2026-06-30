from pathlib import Path

from scripts.integrations import (
    run_diffusion_planner_dp_camp_v13_result_readiness_rejected_nonoverlap_remediation_collection
    as remediation,
)


def test_remediation_commands_are_default_off_provenance_only(tmp_path: Path) -> None:
    routes = [
        {"name": "sample_normal", "path": "/assets/sample_normal.pkl"},
        {"name": "sample_tl", "path": "/assets/sample_tl.pkl"},
        {"name": "nishi_release", "path": "/assets/nishi_release.pkl"},
        {"name": "nishi_lane_change", "path": "/assets/nishi_lane_change.pkl"},
    ]

    commands = remediation._planned_commands(
        artifact_dir=tmp_path,
        camp_repo=Path("/camp"),
        diffusion_repo=Path("/dp"),
        python_executable=Path("/venv/bin/python"),
        runtime_manifest_json=tmp_path / "runtime.json",
        previous_training_output_dir=Path("/training"),
        assets_dir=Path("/assets"),
        routes=routes,
        seeds=(1300, 1301),
        max_npcs_values=(0, 4),
        traffic_light_modes=("on", "off"),
        steps=100,
        num_candidates=8,
        spawn_probability=0.3,
        device="cuda",
    )

    assert len(commands) == 32
    joined = "\n".join(" ".join(row["command"]) for row in commands)
    assert "--camp_default_off_shadow_selector" in joined
    assert "--camp_candidate_tensor_provenance_logging" in joined
    assert "--camp_collect_closed_loop_outcomes" not in joined
    assert "--candidate_reference_blend_steps" not in joined
    assert "--candidate_guidance_config" not in joined
    assert "--candidate_guidance_scale" not in joined
    assert "--camp_traffic_light_hybrid_postselection" not in joined
    assert all("/planned_shadow_replay_evaluation/selection_logs/" not in row["output_dir"] for row in commands)


def test_remediation_readiness_accepts_clean_nonoverlap_summary() -> None:
    record_summary = {
        "records_total": 3200,
        "candidate_count_values": {"8": 3200},
        "atom_schema_versions": {"dp_camp_v10_14d": 3200},
        "atom_count_values": {"14": 3200},
        "formal_seed_records": 0,
        "closed_loop_outcome_records": 0,
        "reference_blend_enabled_records": 0,
        "guidance_enabled_records": 0,
        "postselection_records": 0,
        "camp_candidate_generation_effect_records": 0,
        "dp_modification_records": 0,
        "default_off_shadow_selector_valid_records": 3200,
        "camp_candidate_tensor_provenance_records": 3200,
        "selected_index_counts": {"0": 3200},
        "executed_index_counts": {"0": 3200},
        "route_records": {
            "sample_normal": 800,
            "sample_tl": 800,
            "nishi_release": 800,
            "nishi_lane_change": 800,
        },
        "seed_records": {"1300": 1600, "1301": 1600},
        "route_tl_records": {f"bucket_{index}": 400 for index in range(8)},
        "usable_feasible_records": 2653,
        "multi_feasible_records": 2593,
        "finite_reward_records": 3200,
    }
    nonoverlap = {
        "eval_hashes_in_previous_count": 0,
        "candidate_hash_intersection_count": 0,
        "path_signature_intersection_count": 0,
        "record_identity_intersection_count": 0,
        "split_manifest_root_intersection_count": 0,
    }

    failures = remediation._readiness_failures(
        selection_logs=[Path(f"log_{index}.json") for index in range(32)],
        clean_contract={
            "passed": True,
            "records": 3200,
            "future_training_input_contract_satisfied": True,
        },
        record_summary=record_summary,
        nonoverlap=nonoverlap,
    )

    assert failures == []
