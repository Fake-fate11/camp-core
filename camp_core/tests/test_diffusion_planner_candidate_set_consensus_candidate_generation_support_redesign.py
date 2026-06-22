from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_availability_diversity_synthesis import (
    AUTHORIZED_NEXT_WORK as SOURCE_AUTHORIZED_NEXT_WORK,
    READY_STATUS as SOURCE_READY_STATUS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_candidate_generation_support_redesign import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


SYNTHESIS_JSON = (
    "candidate_set_consensus_candidate_availability_diversity_synthesis_plan.json"
)
SYNTHESIS_MD = (
    "candidate_set_consensus_candidate_availability_diversity_synthesis_plan.md"
)


def _write_sha256sums(root: Path, names: tuple[str, ...]) -> None:
    lines = []
    for name in names:
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _synthesis_payload(
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
            "candidate_availability_diversity_synthesis_plan_ready": passed,
            "candidate_generation_support_redesign_plan_authorized": passed,
            "selected_next_work": SOURCE_AUTHORIZED_NEXT_WORK,
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
        "synthesis_plan": {
            "selected_next_work": SOURCE_AUTHORIZED_NEXT_WORK,
        },
    }


def _write_synthesis_root(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
    exit_code: str = "0",
) -> Path:
    root = tmp_path / "synthesis"
    root.mkdir()
    (root / SYNTHESIS_JSON).write_text(
        json.dumps(payload or _synthesis_payload()),
        encoding="utf-8",
    )
    (root / SYNTHESIS_MD).write_text("# synthesis\n", encoding="utf-8")
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
            SYNTHESIS_JSON,
            SYNTHESIS_MD,
            "COMMAND.log",
            "COMMAND.err",
            "EXIT_CODE",
            "HEADS.txt",
        ),
    )
    return root


def test_support_redesign_plan_ready(tmp_path: Path) -> None:
    report = build_report(
        synthesis_root=_write_synthesis_root(tmp_path),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )
    decision = report["final_decision"]
    plan = report["support_redesign_plan"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["candidate_generation_support_redesign_plan_ready"] is True
    assert decision["route_topology_comfort_support_preflight_authorized"] is True
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert plan["selection_type"] == "fresh_preflight_only_gate"
    assert plan["selected_next_work"] == AUTHORIZED_NEXT_WORK
    family_names = {item["name"] for item in plan["rejected_or_blocked_families"]}
    assert "source_donor_graft_or_world_frame_bridge" in family_names
    assert "constant_deceleration_red_stop_margin_tuning" in family_names


def test_support_redesign_rejects_synthesis_sha_mismatch(tmp_path: Path) -> None:
    root = _write_synthesis_root(tmp_path)
    (root / SYNTHESIS_MD).write_text("# mutated\n", encoding="utf-8")

    report = build_report(
        synthesis_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "synthesis_sha256sums_ok" in report["final_decision"]["failed_checks"]


def test_support_redesign_rejects_dp_mismatch(tmp_path: Path) -> None:
    report = build_report(
        synthesis_root=_write_synthesis_root(tmp_path),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head="wrong",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_support_redesign_rejects_source_not_ready(tmp_path: Path) -> None:
    report = build_report(
        synthesis_root=_write_synthesis_root(
            tmp_path,
            payload=_synthesis_payload(status="candidate_set_consensus_bad", passed=False),
        ),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_status" in failed
    assert "source_passed" in failed
    assert report["final_decision"]["authorized_next_work"] is None


def test_support_redesign_rejects_source_blocked_action(tmp_path: Path) -> None:
    report = build_report(
        synthesis_root=_write_synthesis_root(
            tmp_path,
            payload=_synthesis_payload(blocked_action=True),
        ),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_support_redesign_markdown_boundaries(tmp_path: Path) -> None:
    report = build_report(
        synthesis_root=_write_synthesis_root(tmp_path),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    markdown = render_markdown(report)

    assert "Candidate-Generation Support Redesign Plan" in markdown
    assert "route/topology comfort-support preflight" in markdown
    assert "plan-only" in markdown
    assert "preflight-only" in markdown
    assert "no candidate generation execution" in markdown
    assert "no replay" in markdown
    assert "formal seeds" in markdown
    assert "DP weights and DP code must remain fixed" in markdown
    assert "classical Benders" in markdown


def test_support_redesign_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _write_synthesis_root(tmp_path)
    output_json = tmp_path / "support_redesign.json"
    output_md = tmp_path / "support_redesign.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "support-redesign-plan",
            "--synthesis_root",
            str(root),
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
    assert "Candidate-Generation Support Redesign Plan" in output_md.read_text(
        encoding="utf-8"
    )
