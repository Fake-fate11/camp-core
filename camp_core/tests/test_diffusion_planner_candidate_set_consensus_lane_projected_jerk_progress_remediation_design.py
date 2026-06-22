from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.integrations.analyze_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_failure_attribution import (
    AUTHORIZED_NEXT_WORK as ANALYSIS_AUTHORIZED_NEXT_WORK,
    READY_STATUS as ANALYSIS_READY_STATUS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_failure_attribution import (
    EXIT_CODE,
    HEADS,
    SHA256SUMS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_remediation_design import (
    ANALYSIS_JSON,
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


def _analysis_payload(
    *,
    status: str = ANALYSIS_READY_STATUS,
    authorized_next_work: str | None = ANALYSIS_AUTHORIZED_NEXT_WORK,
    primary_blocker_family: str = "relative_comfort_support",
) -> dict:
    return {
        "final_decision": {
            "status": status,
            "authorized_next_work": authorized_next_work,
            "candidate_generation_execution_authorized": False,
            "fixed_snapshot_screen_rerun_authorized": False,
            "new_replay_authorized": False,
            "formal_seeds_authorized": False,
            "full36_authorized": False,
            "online_selector_authorized": False,
            "atom_promotion_authorized": False,
            "camp_retraining_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
        },
        "source_summary": {
            "screen": {
                "generated_candidate_rows": 276,
                "comfort_rows": 0,
            }
        },
        "read_only_attribution": {
            "primary_blocker_family": primary_blocker_family,
            "primary_comfort_blocker": "route_topology_comfort_blocked_command_jerk",
            "primary_hard_blocker": "dp_kinematic",
            "primary_latency_source": "total",
            "absolute_lateral_guard_retained": True,
            "comfort_blocker_ranking": [
                {
                    "name": "route_topology_comfort_blocked_command_jerk",
                    "count": 64,
                    "share_of_generated_rows": 0.2318840579710145,
                },
                {
                    "name": "route_topology_comfort_blocked_rollout_lateral",
                    "count": 63,
                    "share_of_generated_rows": 0.22826086956521738,
                },
            ],
            "hard_blocker_ranking": [
                {
                    "name": "dp_kinematic",
                    "count": 197,
                    "share_of_generated_rows": 0.7137681159420289,
                }
            ],
            "latency_ranking": [
                {
                    "name": "total",
                    "p95_ms": 102.54559572786093,
                    "threshold_ms": 100.0,
                    "gate_passed": False,
                },
                {
                    "name": "candidate_build",
                    "p95_ms": 35.61945259571073,
                    "threshold_ms": 10.0,
                    "gate_passed": False,
                },
            ],
            "absolute_guard_failure_ranking": [
                {
                    "name": "hard_dp_kinematic",
                    "count": 197,
                    "share_of_generated_rows": 0.7137681159420289,
                }
            ],
        },
    }


def _write_sha256sums(root: Path, names: list[str]) -> None:
    lines = []
    for name in names:
        data = (root / name).read_bytes()
        lines.append(f"{hashlib.sha256(data).hexdigest()}  {name}")
    (root / SHA256SUMS).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_analysis_root(
    tmp_path: Path,
    payload: dict | None = None,
) -> Path:
    root = tmp_path / "analysis"
    root.mkdir()
    (root / ANALYSIS_JSON).write_text(
        json.dumps(payload or _analysis_payload(), indent=2) + "\n",
        encoding="utf-8",
    )
    (root / EXIT_CODE).write_text("0\n", encoding="utf-8")
    (root / HEADS).write_text("HEADS\n", encoding="utf-8")
    _write_sha256sums(root, [ANALYSIS_JSON, EXIT_CODE, HEADS])
    return root


def _build(tmp_path: Path, payload: dict | None = None) -> dict:
    root = _write_analysis_root(tmp_path, payload)
    return build_report(
        analysis_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )


def test_remediation_design_plan_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)

    decision = report["final_decision"]
    design = report["remediation_design"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert design["selected_next_work"] == AUTHORIZED_NEXT_WORK
    assert design["design_priorities"][0]["focus"].startswith(
        "restore relative comfort support"
    )
    assert len(design["remediation_threads"]) == 3


def test_remediation_design_rejects_sha_mismatch(tmp_path: Path) -> None:
    root = _write_analysis_root(tmp_path)
    (root / ANALYSIS_JSON).write_text("{}", encoding="utf-8")

    report = build_report(
        analysis_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "analysis_sha256sums_ok" in report["final_decision"]["failed_checks"]


def test_remediation_design_rejects_dp_mismatch(tmp_path: Path) -> None:
    root = _write_analysis_root(tmp_path)

    report = build_report(
        analysis_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head="wrong",
        label="unit",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_remediation_design_rejects_missing_authorization(tmp_path: Path) -> None:
    payload = _analysis_payload(authorized_next_work="not_allowed")
    report = _build(tmp_path, payload)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "analysis_authorizes_remediation_design" in report["final_decision"][
        "failed_checks"
    ]


def test_remediation_design_rejects_wrong_blocker_family(tmp_path: Path) -> None:
    payload = _analysis_payload(primary_blocker_family="latency")
    report = _build(tmp_path, payload)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "primary_blocker_family_relative_comfort" in report["final_decision"][
        "failed_checks"
    ]


def test_remediation_design_rejects_missing_latency_ranking(tmp_path: Path) -> None:
    payload = _analysis_payload()
    payload["read_only_attribution"]["latency_ranking"] = []
    report = _build(tmp_path, payload)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "latency_ranking_present" in report["final_decision"]["failed_checks"]


def test_remediation_design_markdown_boundaries(tmp_path: Path) -> None:
    report = _build(tmp_path)
    markdown = render_markdown(report)

    assert "Remediation Design Plan" in markdown
    assert "Design Priorities" in markdown
    assert "relative comfort" in markdown
    assert "hard-feasibility" in markdown
    assert "latency" in markdown
    assert "candidate generation execution is not authorized" in markdown
    assert "fixed-snapshot screen rerun is not authorized" in markdown
    assert "replay is not authorized" in markdown
    assert "formal seeds 11/12/13 remain frozen" in markdown
    assert "DP weights and DP code must remain fixed" in markdown
    assert "classical Benders" in markdown


def test_remediation_design_cli_writes_outputs(tmp_path: Path, monkeypatch) -> None:
    root = _write_analysis_root(tmp_path)
    output_json = tmp_path / "out" / "plan.json"
    output_md = tmp_path / "out" / "plan.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan",
            "--analysis_root",
            str(root),
            "--camp_head",
            "abc",
            "--camp_origin_main",
            "abc",
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

    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["final_decision"]["status"] == READY_STATUS
    assert output_md.read_text(encoding="utf-8").startswith(
        "# Lane-Projected Jerk/Progress Remediation Design Plan"
    )
