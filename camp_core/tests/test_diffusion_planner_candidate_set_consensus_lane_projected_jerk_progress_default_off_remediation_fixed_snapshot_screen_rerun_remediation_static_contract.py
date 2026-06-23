from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_remediation_fixed_snapshot_screen_rerun_remediation_design import (
    AUTHORIZED_NEXT_WORK as DESIGN_AUTHORIZED_NEXT_WORK,
    READY_STATUS as DESIGN_READY_STATUS,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_default_off_remediation_fixed_snapshot_screen_rerun_remediation_static_contract import (
    AUTHORIZED_NEXT_WORK,
    DESIGN_EXIT,
    DESIGN_JSON,
    HEADS,
    READY_STATUS,
    REJECT_STATUS,
    SHA256SUMS,
    build_report,
    main,
    render_markdown,
)


def _design_payload(
    *,
    status: str = DESIGN_READY_STATUS,
    authorized_next_work: str | None = DESIGN_AUTHORIZED_NEXT_WORK,
    threads: list[str] | None = None,
    blocked_action: bool = False,
) -> dict[str, object]:
    thread_names = threads or [
        "relative_comfort_static_contract",
        "hard_blocker_separation_contract",
        "latency_static_contract",
        "absolute_guard_subset_contract",
    ]
    return {
        "final_decision": {
            "status": status,
            "authorized_next_work": authorized_next_work,
            "implementation_authorized": False,
            "candidate_generation_execution_authorized": False,
            "fixed_snapshot_screen_rerun_authorized": False,
            "fixed_snapshot_screen_rerun_execution_authorized": False,
            "new_replay_authorized": False,
            "formal_seeds_authorized": False,
            "full36_authorized": False,
            "online_selector_authorized": False,
            "atom_promotion_authorized": blocked_action,
            "camp_retraining_authorized": False,
            "dp_modification_authorized": False,
            "safety_benefit_evidence": False,
            "camp_over_dp_top1_claim_authorized": False,
            "classic_benders_claim_authorized": False,
        },
        "remediation_design": {
            "selected_next_work": DESIGN_AUTHORIZED_NEXT_WORK,
            "remediation_threads": [{"name": name} for name in thread_names],
            "next_gate_checks": [
                "read-only source and artifact inspection only",
                "no candidate generation and no fixed-snapshot screen rerun",
            ],
        },
    }


def _source_text() -> str:
    return """
def parse_args():
    parser.add_argument("--generator_policy", choices=("lane_projected_jerk_progress_red_stop",), default="lane_centerline_red_stop")

def reward_hard_feasibility(): pass
hard_reasons = []
hard_reason_counts = {}
route_topology_dp_kinematic = "route_topology_dp_kinematic"
route_topology_dp_road_border = "route_topology_dp_road_border"
route_topology_lane_invalid = "route_topology_lane_invalid"
route_topology_red_timing_invalid = "route_topology_red_timing_invalid"

def _comfort_admissible(): pass
def _comfort_failure_classes(): pass
route_topology_comfort_blocked_command_jerk = "route_topology_comfort_blocked_command_jerk"
route_topology_comfort_blocked_command_lateral = "route_topology_comfort_blocked_command_lateral"
route_topology_comfort_blocked_progress_loss = "route_topology_comfort_blocked_progress_loss"
route_topology_comfort_blocked_rollout_distance = "route_topology_comfort_blocked_rollout_distance"
route_topology_comfort_blocked_rollout_jerk = "route_topology_comfort_blocked_rollout_jerk"
route_topology_comfort_blocked_rollout_lateral = "route_topology_comfort_blocked_rollout_lateral"
progress_comfort_delta = {}

def timing():
    time.perf_counter()
    latency_ms = {"candidate_build": 1, "total": 2}
def _summarize_latency(): pass

absolute_lateral_guard = True
route_topology_default_off_remediation_absolute_lateral_guard = "route_topology_default_off_remediation_absolute_lateral_guard"
absolute_lateral_guard_rows = 28
absolute_lateral_guard_snapshot_support_rate = 0.33
"""


def _write_sha256sums(root: Path, names: tuple[str, ...]) -> None:
    lines = []
    for name in names:
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (root / SHA256SUMS).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_design_root(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
    design_exit: str = "0",
) -> Path:
    root = tmp_path / "design"
    root.mkdir()
    (root / DESIGN_JSON).write_text(
        json.dumps(payload or _design_payload(), indent=2) + "\n",
        encoding="utf-8",
    )
    (root / DESIGN_EXIT).write_text(f"{design_exit}\n", encoding="utf-8")
    (root / HEADS).write_text(
        f"CAMP_HEAD=head\nDP_HEAD={EXPECTED_DP_HEAD}\n",
        encoding="utf-8",
    )
    _write_sha256sums(root, (DESIGN_JSON, DESIGN_EXIT, HEADS))
    return root


def _write_source(tmp_path: Path, text: str | None = None) -> Path:
    path = tmp_path / "analyze_diffusion_planner_route_topology_candidate_screen.py"
    path.write_text(text or _source_text(), encoding="utf-8")
    return path


def _build(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
    source_text: str | None = None,
) -> dict[str, object]:
    return build_report(
        design_root=_write_design_root(tmp_path, payload=payload),
        source_path=_write_source(tmp_path, source_text),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )


def test_default_off_rerun_static_contract_review_complete(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]
    review = report["static_contract_review"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["implementation_authorized"] is False
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert [item["name"] for item in review["contracts"]] == [
        "relative_comfort_static_contract",
        "hard_blocker_separation_contract",
        "latency_static_contract",
        "absolute_guard_subset_contract",
        "policy_default_off_contract",
    ]


def test_default_off_rerun_static_contract_rejects_sha_mismatch(
    tmp_path: Path,
) -> None:
    root = _write_design_root(tmp_path)
    source = _write_source(tmp_path)
    (root / DESIGN_JSON).write_text("{}", encoding="utf-8")

    report = build_report(
        design_root=root,
        source_path=source,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "design_sha256sums_ok" in report["final_decision"]["failed_checks"]


def test_default_off_rerun_static_contract_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = build_report(
        design_root=_write_design_root(tmp_path),
        source_path=_write_source(tmp_path),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head="wrong",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_default_off_rerun_static_contract_rejects_missing_authorization(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_design_payload(authorized_next_work="not_allowed"),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "design_authorizes_static_contract_review" in report["final_decision"][
        "failed_checks"
    ]


def test_default_off_rerun_static_contract_rejects_missing_design_thread(
    tmp_path: Path,
) -> None:
    report = _build(
        tmp_path,
        payload=_design_payload(threads=["relative_comfort_static_contract"]),
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "design_threads_present" in report["final_decision"]["failed_checks"]


def test_default_off_rerun_static_contract_rejects_source_gap(
    tmp_path: Path,
) -> None:
    source = _source_text().replace("_comfort_admissible", "missing_comfort")
    report = _build(tmp_path, source_text=source)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "contract_relative_comfort_static_contract_present" in report[
        "final_decision"
    ]["failed_checks"]


def test_default_off_rerun_static_contract_rejects_authorization_leak(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, payload=_design_payload(blocked_action=True))

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "design_blocked_actions_clear" in report["final_decision"]["failed_checks"]


def test_default_off_rerun_static_contract_markdown_boundaries(
    tmp_path: Path,
) -> None:
    markdown = render_markdown(_build(tmp_path))

    assert "Static Contract Review" in markdown
    assert "relative_comfort_static_contract" in markdown
    assert "implementation and unit-test changes are not authorized" in markdown
    assert "candidate generation execution is not authorized" in markdown
    assert "fixed-snapshot screen rerun is not authorized" in markdown
    assert "replay is not authorized" in markdown
    assert "formal seeds 11/12/13 remain frozen" in markdown
    assert "DP weights and DP code must remain fixed" in markdown
    assert "CAMP-over-DP-Top-1" in markdown
    assert "classical Benders" in markdown


def test_default_off_rerun_static_contract_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _write_design_root(tmp_path)
    source = _write_source(tmp_path)
    output_json = tmp_path / "out" / "review.json"
    output_md = tmp_path / "out" / "review.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "review",
            "--design_root",
            str(root),
            "--source_path",
            str(source),
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
        "# Default-Off Fixed-Snapshot Rerun Remediation Static Contract Review"
    )
