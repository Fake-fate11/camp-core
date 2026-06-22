from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_candidate_generation_support_redesign import (
    AUTHORIZED_NEXT_WORK as SOURCE_AUTHORIZED_NEXT_WORK,
    READY_STATUS as SOURCE_READY_STATUS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_route_topology_comfort_support_preflight import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


SOURCE_JSON = "candidate_set_consensus_candidate_generation_support_redesign_plan.json"
SOURCE_MD = "candidate_set_consensus_candidate_generation_support_redesign_plan.md"


def _write_sha256sums(root: Path, names: tuple[str, ...]) -> None:
    lines = []
    for name in names:
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _source_payload(
    *,
    status: str = SOURCE_READY_STATUS,
    passed: bool = True,
    blocked_action: bool = False,
) -> dict[str, object]:
    return {
        "final_decision": {
            "status": status,
            "passed": passed,
            "authorized_next_work": SOURCE_AUTHORIZED_NEXT_WORK,
            "candidate_generation_support_redesign_plan_ready": passed,
            "route_topology_comfort_support_preflight_authorized": passed,
            "selected_next_work": SOURCE_AUTHORIZED_NEXT_WORK,
            "candidate_generation_execution_authorized": False,
            "safety_benefit_evidence": False,
            "atom_promotion_authorized": blocked_action,
            "new_replay_authorized": False,
            "closed_loop_smoke_authorized": False,
            "closed_loop_replay_authorized": False,
            "formal_seeds_authorized": False,
            "full36_authorized": False,
            "online_selector_authorized": False,
            "online_selector_promotion_authorized": False,
            "camp_retraining_authorized": False,
            "training_execution_authorized": False,
            "dp_modification_authorized": False,
            "classic_benders_claim_authorized": False,
            "failed_checks": [],
        },
        "support_redesign_plan": {
            "selected_next_work": SOURCE_AUTHORIZED_NEXT_WORK,
        },
    }


def _write_source_root(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
    exit_code: str = "0",
) -> Path:
    root = tmp_path / "support_redesign"
    root.mkdir()
    (root / SOURCE_JSON).write_text(
        json.dumps(payload or _source_payload()),
        encoding="utf-8",
    )
    (root / SOURCE_MD).write_text("# support redesign\n", encoding="utf-8")
    (root / "COMMAND.log").write_text("command\n", encoding="utf-8")
    (root / "COMMAND.err").write_text("", encoding="utf-8")
    (root / "EXIT_CODE").write_text(f"{exit_code}\n", encoding="utf-8")
    (root / "HEADS.txt").write_text(
        f"CAMP_HEAD=head\nDP_HEAD={EXPECTED_DP_HEAD}\n",
        encoding="utf-8",
    )
    _write_sha256sums(
        root,
        (
            SOURCE_JSON,
            SOURCE_MD,
            "COMMAND.log",
            "COMMAND.err",
            "EXIT_CODE",
            "HEADS.txt",
        ),
    )
    return root


def _decision(status: str, **extra: object) -> dict[str, object]:
    decision: dict[str, object] = {"status": status}
    decision.update(extra)
    return {"final_decision": decision}


def _screen(
    *,
    status: str = "route_topology_candidate_support_insufficient",
    hard: float = 0.38,
    comfort: float = 0.0,
    min_rate: float = 0.25,
    rows: int = 10,
) -> dict[str, object]:
    return {
        "final_decision": {"status": status},
        "support_gate": {
            "hard_feasible_snapshot_support_rate": hard,
            "comfort_admissible_snapshot_support_rate": comfort,
            "min_snapshot_support_rate": min_rate,
        },
        "records": {
            "lower_union_red_hard_feasible_rows": rows,
            "lower_union_red_comfort_admissible_rows": 0,
        },
    }


def _absolute_guard(
    *,
    status: str,
    support: float,
    min_rate: float = 0.25,
) -> dict[str, object]:
    return {
        "final_decision": {"status": status},
        "support_gate": {
            "absolute_lateral_guard_snapshot_support_rate": support,
            "min_snapshot_support_rate": min_rate,
        },
        "records": {
            "lower_union_red_hard_progress_rows": 8,
            "absolute_lateral_guard_rows": 3,
        },
    }


def _write_evidence(
    tmp_path: Path,
    overrides: dict[str, dict[str, object]] | None = None,
) -> dict[str, Path]:
    payloads = {
        "route_topology_readiness": {
            "final_decision": {
                "status": "route_topology_candidate_design_ready",
                "offline_candidate_augmentation_screen_authorized": True,
            },
            "snapshot_aggregate": {
                "snapshots": 57,
                "ready_snapshot_rate": 1.0,
            },
        },
        "constant_red_stop_screen": _screen(hard=0.38, comfort=0.0),
        "prefix_comfort_screen": _screen(hard=0.14, comfort=0.0),
        "constant_absolute_lateral_guard": _absolute_guard(
            status="route_topology_absolute_lateral_guard_support_insufficient",
            support=0.04,
        ),
        "prefix_absolute_lateral_guard": _absolute_guard(
            status="route_topology_absolute_lateral_guard_support_insufficient",
            support=0.14,
        ),
        "lane_projected_screen": _screen(hard=0.38, comfort=0.0),
        "lane_projected_absolute_lateral_guard": _absolute_guard(
            status="route_topology_absolute_lateral_guard_support_present",
            support=0.33,
        ),
        "prefix_lane_projected_screen": _screen(hard=0.38, comfort=0.0),
        "prefix_lane_projected_absolute_lateral_guard": _absolute_guard(
            status="route_topology_absolute_lateral_guard_support_present",
            support=0.38,
        ),
        "latest_safe_screen": _screen(hard=0.04, comfort=0.0),
        "latest_safe_failure_patterns": _decision(
            "route_topology_failure_patterns_hard_support_insufficient",
        ),
    }
    for name, payload in (overrides or {}).items():
        payloads[name] = payload

    paths = {}
    for name, payload in payloads.items():
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths[name] = path
    return paths


def test_route_topology_comfort_support_preflight_ready(tmp_path: Path) -> None:
    report = build_report(
        support_redesign_root=_write_source_root(tmp_path),
        evidence_paths=_write_evidence(tmp_path),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )
    decision = report["final_decision"]
    preflight = report["preflight_plan"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["route_topology_comfort_support_preflight_ready"] is True
    assert decision["lane_projected_jerk_progress_support_design_plan_authorized"] is True
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert preflight["selection_type"] == "fresh_plan_only_gate"
    assert preflight["selected_next_work"] == AUTHORIZED_NEXT_WORK


def test_route_topology_preflight_rejects_source_sha_mismatch(tmp_path: Path) -> None:
    source = _write_source_root(tmp_path)
    (source / SOURCE_MD).write_text("# mutated\n", encoding="utf-8")

    report = build_report(
        support_redesign_root=source,
        evidence_paths=_write_evidence(tmp_path),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "support_redesign_sha256sums_ok" in report["final_decision"]["failed_checks"]


def test_route_topology_preflight_rejects_dp_mismatch(tmp_path: Path) -> None:
    report = build_report(
        support_redesign_root=_write_source_root(tmp_path),
        evidence_paths=_write_evidence(tmp_path),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head="wrong",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_route_topology_preflight_rejects_source_not_ready(tmp_path: Path) -> None:
    report = build_report(
        support_redesign_root=_write_source_root(
            tmp_path,
            payload=_source_payload(status="candidate_set_consensus_bad", passed=False),
        ),
        evidence_paths=_write_evidence(tmp_path),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_status" in failed
    assert "source_passed" in failed
    assert report["final_decision"]["authorized_next_work"] is None


def test_route_topology_preflight_rejects_source_blocked_action(tmp_path: Path) -> None:
    report = build_report(
        support_redesign_root=_write_source_root(
            tmp_path,
            payload=_source_payload(blocked_action=True),
        ),
        evidence_paths=_write_evidence(tmp_path),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_route_topology_preflight_rejects_wrong_evidence_status(tmp_path: Path) -> None:
    report = build_report(
        support_redesign_root=_write_source_root(tmp_path),
        evidence_paths=_write_evidence(
            tmp_path,
            {
                "route_topology_readiness": _decision("unexpected"),
            },
        ),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "evidence_route_topology_readiness_status" in report["final_decision"]["failed_checks"]


def test_route_topology_preflight_rejects_missing_lane_projected_support(
    tmp_path: Path,
) -> None:
    report = build_report(
        support_redesign_root=_write_source_root(tmp_path),
        evidence_paths=_write_evidence(
            tmp_path,
            {
                "lane_projected_absolute_lateral_guard": _absolute_guard(
                    status="route_topology_absolute_lateral_guard_support_insufficient",
                    support=0.10,
                ),
            },
        ),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "evidence_lane_projected_absolute_lateral_guard_status" in failed
    assert "lane_projected_absolute_lateral_guard_support_at_or_above_min" in failed


def test_route_topology_preflight_markdown_boundaries(tmp_path: Path) -> None:
    report = build_report(
        support_redesign_root=_write_source_root(tmp_path),
        evidence_paths=_write_evidence(tmp_path),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    markdown = render_markdown(report)

    assert "Route/Topology Comfort-Support Preflight" in markdown
    assert "lane-projected" in markdown
    assert "jerk" in markdown
    assert "progress" in markdown
    assert "preflight-only" in markdown
    assert "plan-only" in markdown
    assert "no candidate generation execution" in markdown
    assert "no replay" in markdown
    assert "formal seeds" in markdown
    assert "DP weights and DP code must remain fixed" in markdown
    assert "classical Benders" in markdown


def test_route_topology_preflight_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _write_source_root(tmp_path)
    evidence_paths = _write_evidence(tmp_path)
    output_json = tmp_path / "preflight.json"
    output_md = tmp_path / "preflight.md"
    evidence_args = [
        item
        for name, path in sorted(evidence_paths.items())
        for item in ("--evidence_json", f"{name}={path}")
    ]
    monkeypatch.setattr(
        "sys.argv",
        [
            "route-topology-comfort-support-preflight",
            "--support_redesign_root",
            str(source),
            *evidence_args,
            "--camp_head",
            "abc",
            "--camp_origin_main",
            "abc",
            "--dp_head",
            EXPECTED_DP_HEAD,
            "--label",
            "unit_cli",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["analysis"]["label"] == "unit_cli"
    assert payload["final_decision"]["status"] == READY_STATUS
    assert payload["final_decision"]["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert "Route/Topology Comfort-Support Preflight" in output_md.read_text(
        encoding="utf-8"
    )
