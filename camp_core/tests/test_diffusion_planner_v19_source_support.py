from __future__ import annotations

import importlib
import json
from pathlib import Path

import numpy as np
import pytest


def _source_support():
    try:
        return importlib.import_module(
            "scripts.integrations.audit_diffusion_planner_dp_camp_v19_source_support"
        )
    except ModuleNotFoundError:
        pytest.fail("the v19 source-support census script is missing")


def _row(
    bucket: str,
    selection_tag: str,
    log_token: str,
    scene_token: str,
    scenario_token: str | None = None,
    *,
    location: str = "us-nv-las-vegas-strip",
) -> dict[str, object]:
    return {
        "bucket": bucket,
        "selection_tag": selection_tag,
        "tags": [selection_tag],
        "location": location,
        "log_token": log_token,
        "logfile": log_token,
        "scene_token": scene_token,
        "scene_name": scene_token,
        "scenario_token": scenario_token or f"scenario-{scene_token}",
        "timestamp_us": 3_000_000,
        "past_span_s": 3.0,
        "future_span_s": 8.0,
        "mission_goal_available": True,
        "route_roadblock_count": 2,
        "route_unique": True,
        "route_connected": True,
        "valid_route_slot_count": 2,
        "finite_positive_speed_slot_count": 2,
        "full_window_source_complete": False,
        "candidate_local_any": False,
        "candidate_local_eligible_count": 0,
        "dp_default_source_complete": False,
        "v18_log_overlap": False,
        "v18_scene_overlap": False,
        "failure_class": None,
        "failure_reason": None,
    }


def _candidate_local(row: dict[str, object]) -> dict[str, object]:
    row.update(
        candidate_local_any=True,
        candidate_local_eligible_count=2,
        dp_default_source_complete=True,
    )
    return row


def test_full_window_pair_wins_before_candidate_local_support() -> None:
    module = _source_support()
    normal = _candidate_local(
        _row("normal", "medium_magnitude_speed", "log-a", "scene-a")
    )
    interaction = _candidate_local(
        _row("interaction", "near_multiple_vehicles", "log-b", "scene-b")
    )
    normal["full_window_source_complete"] = True
    interaction["full_window_source_complete"] = True

    selected = module.choose_protocol([interaction, normal])

    assert selected["selected"] is True
    assert selected["exhausted"] is False
    assert selected["rung"] == "full_window_exact_speed"
    assert selected["speed_source_policy"] == "full_window_exact_speed"
    assert [row["bucket"] for row in selected["selected_scenarios"]] == [
        "normal",
        "interaction",
    ]
    assert selected["support_by_tag"]["medium_magnitude_speed"][
        "full_window_exact_speed"
    ] == 1
    assert selected["support_by_location"]["us-nv-las-vegas-strip"][
        "full_window_exact_speed"
    ] == 2
    assert selected["rejection_counts"] == {}


def test_candidate_local_pair_requires_candidate0_and_any_k8_in_both_buckets() -> None:
    module = _source_support()
    normal = _candidate_local(
        _row("normal", "following_lane_without_lead", "log-a", "scene-a")
    )
    interaction = _candidate_local(
        _row(
            "interaction",
            "waiting_for_pedestrian_to_cross",
            "log-b",
            "scene-b",
        )
    )
    interaction["dp_default_source_complete"] = False
    assert module.choose_protocol([normal, interaction])["selected"] is False

    interaction["dp_default_source_complete"] = True
    selected = module.choose_protocol([normal, interaction])
    assert selected["rung"] == "candidate_local_exact_speed"


def test_interaction_only_rung_keeps_honest_bucket_names() -> None:
    module = _source_support()
    rows = [
        _candidate_local(
            _row(
                "interaction",
                "near_multiple_vehicles",
                "log-a",
                "scene-a",
            )
        ),
        _candidate_local(
            _row(
                "interaction",
                "waiting_for_pedestrian_to_cross",
                "log-b",
                "scene-b",
            )
        ),
    ]

    selected = module.choose_protocol(rows)

    assert selected["rung"] == "interaction_only_candidate_local_exact_speed"
    assert [row["bucket"] for row in selected["selected_scenarios"]] == [
        "interaction",
        "interaction",
    ]
    assert len({row["selection_tag"] for row in selected["selected_scenarios"]}) == 2


def test_protocol_selection_uses_frozen_sha_order_and_distinct_identities() -> None:
    module = _source_support()
    rows = [
        _candidate_local(
            _row("normal", "medium_magnitude_speed", "log-a", "scene-a", "z")
        ),
        _candidate_local(
            _row("normal", "medium_magnitude_speed", "log-b", "scene-b", "a")
        ),
        _candidate_local(
            _row("interaction", "near_multiple_vehicles", "log-a", "scene-c", "x")
        ),
        _candidate_local(
            _row("interaction", "near_multiple_vehicles", "log-c", "scene-d", "y")
        ),
    ]
    for row in rows:
        row["selection_sha256"] = "not-trusted"

    selected = module.choose_protocol(rows)
    chosen = selected["selected_scenarios"]

    for row in chosen:
        assert row["selection_sha256"] == module.selection_sha256(
            str(row["bucket"]), row
        )
    assert len({row["log_token"] for row in chosen}) == 2
    assert len({row["scene_token"] for row in chosen}) == 2


def test_no_support_exhausts_without_smoke_config(tmp_path: Path) -> None:
    module = _source_support()
    result = module.choose_protocol(
        [_row("normal", "medium_magnitude_speed", "log-a", "scene-a")]
    )

    assert result["selected"] is False
    assert result["exhausted"] is True
    assert result["rung"] is None

    module.write_census_artifact(
        rows=[],
        output_root=tmp_path / "census",
        source_loader=lambda _row: pytest.fail("no source row expected"),
        source_probe=lambda _row, _source: pytest.fail("no probe expected"),
    )
    assert not (tmp_path / "census" / "smoke_config.json").exists()
    progress = json.loads(
        (tmp_path / "census" / "progress.json").read_text("utf-8")
    )
    assert progress["processed_identities"] == 0
    assert progress["total_identities"] == 0


def test_census_serializes_every_rejection_and_deterministic_candidates(
    tmp_path: Path,
) -> None:
    module = _source_support()
    rows = [
        _row("normal", "medium_magnitude_speed", "log-b", "scene-b"),
        _row("interaction", "near_multiple_vehicles", "log-a", "scene-a"),
        _row("normal", "medium_magnitude_speed", "log-v18", "scene-v18"),
    ]
    rows[2]["v18_log_overlap"] = True
    source_calls = []
    probe_calls = []

    def load_source(row):
        source_calls.append(row["scenario_token"])
        if row["bucket"] == "normal":
            raise ValueError("route is disconnected")
        return {
            "full_window_source_complete": False,
            "valid_route_slot_count": 2,
            "finite_positive_speed_slot_count": 1,
        }

    def probe(row, source):
        probe_calls.append(row["scenario_token"])
        candidates = np.zeros((8, 80, 4), dtype=np.float32)
        candidates[:, :, 0] = len(probe_calls)
        return {
            "candidates": candidates,
            "route_speed_source_eligible_mask": np.array(
                [True, False, True, False, False, False, False, False]
            ),
        }

    output = tmp_path / "census"
    report = module.write_census_artifact(
        rows=rows,
        output_root=output,
        source_loader=load_source,
        source_probe=probe,
    )

    persisted = [
        json.loads(line)
        for line in (output / "census_rows.jsonl").read_text("utf-8").splitlines()
    ]
    assert len(source_calls) == 2
    assert len(probe_calls) == 1
    assert len(persisted) == 3
    assert any(row["failure_reason"] == "route is disconnected" for row in persisted)
    assert any(row["failure_reason"] == "v18_log_overlap" for row in persisted)
    tensors = np.load(output / "candidate_tensors.npy", allow_pickle=False)
    assert tensors.shape == (1, 8, 80, 4)
    tensor_row = next(row for row in persisted if row["candidate_tensor_index"] == 0)
    assert tensor_row["candidate_tensor_sha256"] == module.array_sha256(tensors[0])
    assert report["access_counters"] == {
        "expert_future_value_reads": 0,
        "simulator_advances": 0,
        "metric_computations": 0,
        "outcome_reads": 0,
    }
    matrix = json.loads((output / "support_matrix.json").read_text("utf-8"))
    assert set(matrix["by_log"]) == {"log-a", "log-b", "log-v18"}
    assert set(matrix["by_scene"]) == {"scene-a", "scene-b", "scene-v18"}
    progress = json.loads((output / "progress.json").read_text("utf-8"))
    assert progress["processed_identities"] == 3
    assert progress["total_identities"] == 3
    assert progress["source_probe_count"] == 1
    assert progress["candidate_tensor_bytes"] == tensors.nbytes
    assert progress["disk_free_bytes"] > 0
    assert (output / "SHA256SUMS").is_file()
    assert (output / "ROOT_SHA256").is_file()


def test_census_refuses_existing_output_before_source_access(tmp_path: Path) -> None:
    module = _source_support()
    output = tmp_path / "existing"
    output.mkdir()
    called = []

    with pytest.raises(FileExistsError):
        module.write_census_artifact(
            rows=[_row("normal", "medium_magnitude_speed", "log-a", "scene-a")],
            output_root=output,
            source_loader=lambda row: called.append(row),
            source_probe=lambda _row, _source: {},
        )

    assert called == []


def test_source_probe_command_requires_explicit_operation(tmp_path: Path) -> None:
    module = _source_support()

    with pytest.raises(ValueError, match="source_probe operation"):
        module._source_probe(
            probe_root=tmp_path / "probe",
            worker_command=("python", "worker.py", "{request_dir}"),
            camp_head="a" * 40,
            dp_head="b" * 40,
            nuplan_head="c" * 40,
            selector_hashes=("d" * 64, "e" * 64, "f" * 64),
        )


def test_review_recomputes_masks_without_worker_calls(tmp_path: Path) -> None:
    module = _source_support()
    row = _candidate_local(
        _row("interaction", "near_multiple_vehicles", "log-a", "scene-a")
    )
    census = tmp_path / "census"
    module.write_census_artifact(
        rows=[row],
        output_root=census,
        source_loader=lambda _row: {
            "full_window_source_complete": False,
            "valid_route_slot_count": 2,
            "finite_positive_speed_slot_count": 1,
        },
        source_probe=lambda _row, _source: {
            "candidates": np.zeros((8, 80, 4), dtype=np.float32),
            "route_speed_source_eligible_mask": np.ones(8, dtype=bool),
        },
    )
    reviewed = []

    report = module.write_review_artifact(
        source_root=census,
        output_root=tmp_path / "review",
        source_reviewer=lambda persisted, candidates: reviewed.append(
            (persisted["scenario_token"], candidates.shape)
        )
        or {
            "full_window_source_complete": False,
            "route_speed_source_eligible_mask": np.ones(8, dtype=bool),
        },
    )

    assert reviewed == [(row["scenario_token"], (8, 80, 4))]
    assert report["passed"] is True
    assert report["worker_calls"] == 0
    assert report["simulator_advances"] == 0
    assert report["metric_computations"] == 0
    review_md = (tmp_path / "review" / "review.md").read_text("utf-8")
    assert "Source-Support Independent Review" in review_md
    assert "worker calls: `0`" in review_md


def test_review_rebuilds_smoke_config_instead_of_copying_tampered_bytes(
    tmp_path: Path,
) -> None:
    module = _source_support()
    rows = [
        _row("normal", "medium_magnitude_speed", "log-a", "scene-a"),
        _row("interaction", "near_multiple_vehicles", "log-b", "scene-b"),
    ]
    census = tmp_path / "census"
    module.write_census_artifact(
        rows=rows,
        output_root=census,
        source_loader=lambda _row: {"full_window_source_complete": True},
        source_probe=lambda _row, _source: {
            "candidates": np.zeros((8, 80, 4), dtype=np.float32),
            "route_speed_source_eligible_mask": np.ones(8, dtype=bool),
        },
        base_smoke_config={
            "schema_version": "test_smoke_v1",
            "selected_scenario_count": 2,
            "selected_scenarios": [],
        },
    )
    smoke_path = census / "smoke_config.json"
    smoke = json.loads(smoke_path.read_text("utf-8"))
    smoke["tampered_after_selection"] = True
    smoke_path.write_text(json.dumps(smoke, sort_keys=True) + "\n", encoding="utf-8")
    module._seal(census)

    with pytest.raises(ValueError, match="smoke config byte mismatch"):
        module.write_review_artifact(
            source_root=census,
            output_root=tmp_path / "review",
            source_reviewer=lambda _row, _candidates: {
                "full_window_source_complete": True,
                "route_speed_source_eligible_mask": np.ones(8, dtype=bool),
            },
        )
