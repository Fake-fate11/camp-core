from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_post_nonpromotion_next_gate import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


REVIEW_JSON = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_review.json"
)
REVIEW_MD = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_review.md"
)


def _write_sha256sums(root: Path, names: tuple[str, ...]) -> None:
    lines = []
    for name in names:
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _closeout_review_payload(
    *,
    status: str = (
        "candidate_set_consensus_shadow_atom_safety_score_"
        "nonpromotion_closeout_review_ready"
    ),
    passed: bool = True,
    blocked_action: bool = False,
) -> dict[str, object]:
    return {
        "final_decision": {
            "status": status,
            "passed": passed,
            "authorized_next_work": (
                "candidate_set_consensus_post_nonpromotion_next_gate_plan_only"
            ),
            "nonpromotion_closeout_review_ready": passed,
            "nonpromotion_closeout_complete": passed,
            "post_nonpromotion_next_gate_plan_authorized": passed,
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
        "closeout_review": {
            "review_class": "confirmed_nonpromotion_closeout_complete",
            "chain_closed": True,
            "closed_atom_state": "shadow_only_default_off_not_promoted",
            "next_gate_must_be_plan_only": True,
        },
    }


def _write_review_root(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
    exit_code: str = "0",
) -> Path:
    root = tmp_path / "review"
    root.mkdir()
    (root / REVIEW_JSON).write_text(
        json.dumps(payload or _closeout_review_payload()),
        encoding="utf-8",
    )
    (root / REVIEW_MD).write_text("# review\n", encoding="utf-8")
    (root / "COMMAND.log").write_text("command\n", encoding="utf-8")
    (root / "COMMAND.err").write_text("", encoding="utf-8")
    (root / "EXIT_CODE").write_text(f"{exit_code}\n", encoding="utf-8")
    (root / "HEADS.txt").write_text(
        f"CAMP_HEAD=head\nDP_HEAD={EXPECTED_DP_HEAD}\n",
        encoding="utf-8",
    )
    _write_sha256sums(
        root,
        (REVIEW_JSON, REVIEW_MD, "COMMAND.log", "COMMAND.err", "EXIT_CODE", "HEADS.txt"),
    )
    return root


def test_post_nonpromotion_next_gate_plan_ready(tmp_path: Path) -> None:
    root = _write_review_root(tmp_path)

    report = build_report(
        closeout_review_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )
    decision = report["final_decision"]
    plan = report["next_gate_plan"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["post_nonpromotion_next_gate_plan_ready"] is True
    assert decision["candidate_availability_diversity_synthesis_plan_authorized"] is True
    assert plan["selected_next_work"] == AUTHORIZED_NEXT_WORK
    assert plan["broader_replay_consideration_status"] == "already_completed_not_reopened"
    assert plan["safety_score_atom_branch_status"] == "closed_nonpromotion_not_reopened"
    assert decision["new_replay_authorized"] is False
    assert decision["atom_promotion_authorized"] is False


def test_post_nonpromotion_next_gate_rejects_sha_mismatch(tmp_path: Path) -> None:
    root = _write_review_root(tmp_path)
    (root / REVIEW_MD).write_text("# mutated\n", encoding="utf-8")

    report = build_report(
        closeout_review_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "closeout_review_sha256sums_ok" in report["final_decision"]["failed_checks"]


def test_post_nonpromotion_next_gate_rejects_dp_mismatch(tmp_path: Path) -> None:
    root = _write_review_root(tmp_path)

    report = build_report(
        closeout_review_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head="wrong",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_post_nonpromotion_next_gate_rejects_source_not_ready(tmp_path: Path) -> None:
    root = _write_review_root(
        tmp_path,
        payload=_closeout_review_payload(status="candidate_set_consensus_bad", passed=False),
    )

    report = build_report(
        closeout_review_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_status" in failed
    assert "source_passed" in failed
    assert report["final_decision"]["authorized_next_work"] is None


def test_post_nonpromotion_next_gate_rejects_blocked_action(tmp_path: Path) -> None:
    root = _write_review_root(
        tmp_path,
        payload=_closeout_review_payload(blocked_action=True),
    )

    report = build_report(
        closeout_review_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_post_nonpromotion_next_gate_markdown_boundaries(tmp_path: Path) -> None:
    root = _write_review_root(tmp_path)
    report = build_report(
        closeout_review_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    markdown = render_markdown(report)

    assert "Post-Nonpromotion Next-Gate Plan" in markdown
    assert "already_completed_not_reopened" in markdown
    assert "closed_nonpromotion_not_reopened" in markdown
    assert "candidate availability/diversity" in markdown
    assert "formal seeds" in markdown
    assert "DP modification" in markdown
    assert "classical Benders" in markdown


def test_post_nonpromotion_next_gate_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _write_review_root(tmp_path)
    output_json = tmp_path / "next_gate.json"
    output_md = tmp_path / "next_gate.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "post-nonpromotion-next-gate",
            "--closeout_review_root",
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
    assert "Post-Nonpromotion Next-Gate Plan" in output_md.read_text(encoding="utf-8")
