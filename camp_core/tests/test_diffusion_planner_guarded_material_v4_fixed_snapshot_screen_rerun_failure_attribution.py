from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from scripts.integrations.analyze_diffusion_planner_guarded_material_v4_fixed_snapshot_screen_rerun_failure_attribution import (
    BLOCKED_ACTIONS,
    EXPECTED_CAMP_HEAD,
    EXPECTED_DP_HEAD,
    EXPECTED_SOURCE_ARTIFACT_CAMP_HEAD,
    REMEDIATION_PROFILE,
    SCREEN_REJECT_STATUS,
    build_report,
)
from scripts.integrations import (
    analyze_diffusion_planner_guarded_material_v4_fixed_snapshot_screen_rerun_failure_attribution as target,
)


def _candidate(index: int) -> dict[str, object]:
    return {
        "candidate_index": index,
        "candidate_union_red": 0.0,
        "selected_union_red": 40.5,
        "lower_union_red": True,
        "hard_feasible": False,
        "progress_feasible": False,
        "comfort_admissible": False,
        "failure_classes": [
            "route_topology_lane_invalid",
            "route_topology_dp_kinematic",
            "route_topology_dp_road_border",
        ],
        "hard_reasons": ["dp_lane_crossing", "dp_kinematic", "dp_road_border"],
        "candidate_meta": {
            "profile": REMEDIATION_PROFILE,
            "candidate_materialization_v4": True,
            "comfort_first_precheck_report_only": True,
            "candidate0_preserved": True,
            "dp_rows_preserved": True,
            "uses_outcome_labels": False,
            "remediation_descriptor_payload": {
                "diagnostic_descriptor_payload_v4_report_only": True,
                "candidate_materialization_v4": True,
                "comfort_budget_relaxation": False,
                "future_outcome_leakage": False,
                "uses_outcome_labels": False,
                "score_mutation": False,
                "selected_index_mutation": False,
                "online_selector_promotion": False,
                "affine_score_compatible": True,
                "score_contract": "score_k(w)=a_k^T w",
                "top_comfort_blocker": "route_topology_comfort_blocked_command_jerk",
                "secondary_comfort_blocker": "route_topology_comfort_blocked_rollout_lateral",
            },
        },
    }


def _payload(
    *,
    status: str = SCREEN_REJECT_STATUS,
    blocked_authorization: bool = False,
    mutate_score: bool = False,
) -> dict[str, object]:
    rows = []
    candidate_index = 0
    for row_index in range(57):
        if row_index < 20:
            count = 3
        elif row_index == 20:
            count = 13
        else:
            count = 0
        candidates = [_candidate(candidate_index + offset) for offset in range(count)]
        candidate_index += count
        if mutate_score:
            for candidate in candidates:
                meta = candidate["candidate_meta"]
                assert isinstance(meta, dict)
                descriptor = meta["remediation_descriptor_payload"]
                assert isinstance(descriptor, dict)
                descriptor["score_mutation"] = True
        rows.append(
            {
                "snapshot_path": f"/snapshots/camp_microbenchmark_step_{row_index:04d}.npz",
                "selection_step": row_index,
                "selected_index": 7,
                "selected_union_red": 40.5,
                "generated_count": count,
                "candidate_rows": candidates,
                "timings_ms": {},
            }
        )
    decision: dict[str, object] = {
        "status": status,
        "next_step": "inspect failure classes before designing a materially different generator",
        "source_authorization_conflicts": [],
    }
    for key in BLOCKED_ACTIONS:
        decision[key] = False
    if blocked_authorization:
        decision["training_execution_authorized"] = True
    return {
        "analysis": {
            "candidate_generation_executed": True,
            "closed_loop_replay": False,
            "training": False,
            "future_outcome_leakage": False,
            "online_selector_change": False,
            "uses_outcome_labels": False,
        },
        "support_gate": {
            "min_snapshot_support_rate": 0.25,
            "hard_feasible_snapshot_support_rate": 0.0,
            "hard_feasible_snapshot_support_pass": False,
            "comfort_admissible_snapshot_support_rate": 0.0,
            "comfort_admissible_snapshot_support_pass": False,
        },
        "rows": rows,
        "final_decision": decision,
    }


def _write_sha256sums(
    root: Path,
    names: tuple[str, ...],
    *,
    remote_absolute_paths: bool = False,
) -> None:
    lines = []
    for name in names:
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        artifact_path = (
            f"/root/autodl-tmp/fixed_screen_artifact/{name}"
            if remote_absolute_paths
            else str(root / name)
        )
        lines.append(f"{digest}  {artifact_path}")
    (root / target.SHA256SUMS).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_screen_root(
    tmp_path: Path,
    *,
    payload: Optional[dict[str, object]] = None,
    artifact_camp_head: str = EXPECTED_SOURCE_ARTIFACT_CAMP_HEAD,
    remote_absolute_sha_paths: bool = False,
) -> Path:
    root = tmp_path / "screen"
    root.mkdir()
    (root / target.SCREEN_JSON).write_text(
        json.dumps(payload or _payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (root / target.SCREEN_MD).write_text(
        "# Route/Topology Candidate Augmentation Screen\n\nsupport insufficient\n",
        encoding="utf-8",
    )
    (root / target.CANDIDATE_LOG).write_text("screen completed\n", encoding="utf-8")
    (root / target.CANDIDATE_ERR).write_text("", encoding="utf-8")
    (root / target.HEADS).write_text(
        "\n".join(
            [
                f"CAMP_HEAD={artifact_camp_head}",
                f"CAMP_ORIGIN_MAIN={artifact_camp_head}",
                f"DP_HEAD={EXPECTED_DP_HEAD}",
                "SNAPSHOT_COUNT=57",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    _write_sha256sums(
        root,
        (
            target.SCREEN_JSON,
            target.SCREEN_MD,
            target.CANDIDATE_LOG,
            target.CANDIDATE_ERR,
            target.HEADS,
        ),
        remote_absolute_paths=remote_absolute_sha_paths,
    )
    return root


def _build(
    tmp_path: Path,
    *,
    payload: Optional[dict[str, object]] = None,
    camp_head: str = EXPECTED_CAMP_HEAD,
    camp_origin_main: str = EXPECTED_CAMP_HEAD,
    dp_head: str = EXPECTED_DP_HEAD,
    artifact_camp_head: str = EXPECTED_SOURCE_ARTIFACT_CAMP_HEAD,
    remote_absolute_sha_paths: bool = False,
) -> dict[str, object]:
    return build_report(
        screen_root=_write_screen_root(
            tmp_path,
            payload=payload,
            artifact_camp_head=artifact_camp_head,
            remote_absolute_sha_paths=remote_absolute_sha_paths,
        ),
        camp_head=camp_head,
        camp_origin_main=camp_origin_main,
        dp_head=dp_head,
        label="unit",
    )


def test_guarded_material_v4_failure_attribution_complete(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    source = report["source_summary"]
    materialization = report["materialization_summary"]
    attribution = report["read_only_attribution"]

    assert decision["status"] == target.READY_STATUS
    assert decision["authorized_next_work"] == target.AUTHORIZED_NEXT_WORK
    assert decision["failure_attribution_complete"] is True
    assert decision["remediation_design_plan_authorized"] is True
    assert decision["training_execution_authorized"] is False
    assert decision["dp_modification_authorized"] is False
    assert source["snapshots"] == 57
    assert source["snapshots_with_generated_candidates"] == 21
    assert source["generated_candidate_rows"] == 73
    assert source["row_generated_count_sum"] == 73
    assert source["lower_union_red_rows"] == 73
    assert source["hard_feasible_rows"] == 0
    assert source["comfort_admissible_rows"] == 0
    assert source["hard_reason_counts"] == {
        "dp_kinematic": 73,
        "dp_lane_crossing": 73,
        "dp_road_border": 73,
    }
    assert materialization["materialized_rows"] == 73
    assert materialization["report_only_rows"] == 73
    assert materialization["uses_outcome_labels_rows"] == 0
    assert materialization["score_mutation_rows"] == 0
    assert materialization["selector_mutation_rows"] == 0
    assert materialization["profile_counts"] == {REMEDIATION_PROFILE: 73}
    assert attribution["primary_blocker_family"] == (
        "route_topology_hard_constraint_failure_after_v4_materialization"
    )
    assert attribution["positive_support_evidence"] is False
    assert attribution["materialization_contract_ok"] is True
    assert attribution["training_ready"] is False
    assert attribution["failure_class_ranking"][0]["name"] == "route_topology_dp_kinematic"
    assert attribution["hard_reason_ranking"][0]["name"] == "dp_kinematic"


def test_guarded_material_v4_failure_attribution_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, dp_head="wrong")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_guarded_material_v4_failure_attribution_rejects_camp_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, camp_head="wrong")

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "camp_head_matches_origin_main" in report["final_decision"]["failed_checks"]


def test_guarded_material_v4_failure_attribution_accepts_synced_successor_head(
    tmp_path: Path,
) -> None:
    successor = "c58afe3b0be4ffe604c8d589dbfca02c08a04b90"
    report = _build(tmp_path, camp_head=successor, camp_origin_main=successor)

    assert report["final_decision"]["status"] == target.READY_STATUS
    assert report["head_audit"]["analysis_gate_start_camp_head"] == EXPECTED_CAMP_HEAD


def test_guarded_material_v4_failure_attribution_rejects_source_artifact_mismatch(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, artifact_camp_head=EXPECTED_CAMP_HEAD)

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "artifact_camp_head_matches_source" in report["final_decision"][
        "failed_checks"
    ]


def test_guarded_material_v4_failure_attribution_accepts_copied_remote_sha_manifest(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, remote_absolute_sha_paths=True)

    assert report["final_decision"]["status"] == target.READY_STATUS
    assert report["screen_artifact"]["sha256sums_ok"] is True


def test_guarded_material_v4_failure_attribution_rejects_blocked_authorization(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_payload(blocked_authorization=True))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "screen_no_blocked_authorizations" in report["final_decision"][
        "failed_checks"
    ]


def test_guarded_material_v4_failure_attribution_rejects_score_mutation(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_payload(mutate_score=True))

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "v4_no_score_mutation" in report["final_decision"]["failed_checks"]
    assert "materialization_contract_ok" in report["final_decision"]["failed_checks"]


def test_guarded_material_v4_failure_attribution_rejects_sha_mismatch(
    tmp_path: Path,
) -> None:
    root = _write_screen_root(tmp_path)
    (root / target.CANDIDATE_LOG).write_text("mutated after hash\n", encoding="utf-8")
    report = build_report(
        screen_root=root,
        camp_head=EXPECTED_CAMP_HEAD,
        camp_origin_main=EXPECTED_CAMP_HEAD,
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )

    assert report["final_decision"]["status"] == target.REJECT_STATUS
    assert "sha256sums_match" in report["final_decision"]["failed_checks"]


def test_guarded_material_v4_failure_attribution_cli_writes_outputs(
    tmp_path: Path,
) -> None:
    root = _write_screen_root(tmp_path)
    output_json = tmp_path / "attribution.json"
    output_md = tmp_path / "attribution.md"

    result = subprocess.run(
        [
            sys.executable,
            str(Path(target.__file__).resolve()),
            "--screen_root",
            str(root),
            "--camp_head",
            EXPECTED_CAMP_HEAD,
            "--camp_origin_main",
            EXPECTED_CAMP_HEAD,
            "--dp_head",
            EXPECTED_DP_HEAD,
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["final_decision"]["status"] == target.READY_STATUS
    assert "failure_attribution_complete" in result.stdout
    assert "Guarded Material v4 Screen Rerun Failure Attribution" in output_md.read_text(
        encoding="utf-8"
    )
