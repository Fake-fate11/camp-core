from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_nonpromotion_closeout import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


RECORD_JSON = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_record.json"
)
RECORD_MD = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_record.md"
)


def _write_sha256sums(root: Path, names: tuple[str, ...]) -> None:
    lines = []
    for name in names:
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _record_payload(
    *,
    status: str = (
        "candidate_set_consensus_shadow_atom_safety_score_"
        "nonpromotion_closeout_record_ready"
    ),
    passed: bool = True,
    blocked_action: bool = False,
    recorded: bool = True,
) -> dict[str, object]:
    return {
        "final_decision": {
            "status": status,
            "passed": passed,
            "authorized_next_work": (
                "candidate_set_consensus_shadow_atom_safety_score_"
                "nonpromotion_closeout_review_only"
            ),
            "nonpromotion_closeout_record_ready": passed,
            "nonpromotion_closeout_recorded": recorded,
            "nonpromotion_closeout_review_authorized": passed,
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
        "closeout_record": {
            "record_decision": (
                "close_candidate_set_consensus_safety_score_shadow_atom_"
                "without_promotion"
            ),
            "final_atom_state": "shadow_only_default_off_not_promoted",
            "default_off_retained": True,
            "evidence_class": "real_mixed_nonpromotion_not_safety_benefit_proof",
            "safety_benefit_evidence": False,
            "atom_promotion_authorized": False,
            "future_work_boundary": [
                "candidate-set consensus safety-score atom remains shadow-only/default-off",
                "no CAMP retraining, online selector promotion, Full36, formal seeds, replay, new label attachment, or DP modification is authorized",
                "any future work must start from a fresh plan-only gate with current-state audit",
            ],
        },
    }


def _write_record_root(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
    exit_code: str = "0",
) -> Path:
    root = tmp_path / "record"
    root.mkdir()
    (root / RECORD_JSON).write_text(json.dumps(payload or _record_payload()), encoding="utf-8")
    (root / RECORD_MD).write_text("# record\n", encoding="utf-8")
    (root / "COMMAND.log").write_text("command\n", encoding="utf-8")
    (root / "COMMAND.err").write_text("", encoding="utf-8")
    (root / "EXIT_CODE").write_text(f"{exit_code}\n", encoding="utf-8")
    (root / "HEADS.txt").write_text(
        f"CAMP_HEAD=head\nDP_HEAD={EXPECTED_DP_HEAD}\n",
        encoding="utf-8",
    )
    _write_sha256sums(
        root,
        (RECORD_JSON, RECORD_MD, "COMMAND.log", "COMMAND.err", "EXIT_CODE", "HEADS.txt"),
    )
    return root


def test_nonpromotion_closeout_review_ready(tmp_path: Path) -> None:
    root = _write_record_root(tmp_path)

    report = build_report(
        record_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["nonpromotion_closeout_review_ready"] is True
    assert decision["nonpromotion_closeout_complete"] is True
    assert decision["post_nonpromotion_next_gate_plan_authorized"] is True
    assert decision["atom_promotion_authorized"] is False
    assert report["closeout_review"]["review_class"] == (
        "confirmed_nonpromotion_closeout_complete"
    )


def test_nonpromotion_closeout_review_rejects_sha_mismatch(tmp_path: Path) -> None:
    root = _write_record_root(tmp_path)
    (root / RECORD_MD).write_text("# mutated\n", encoding="utf-8")

    report = build_report(
        record_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "record_sha256sums_ok" in report["final_decision"]["failed_checks"]


def test_nonpromotion_closeout_review_rejects_dp_mismatch(tmp_path: Path) -> None:
    root = _write_record_root(tmp_path)

    report = build_report(
        record_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head="wrong",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_nonpromotion_closeout_review_rejects_source_not_ready(tmp_path: Path) -> None:
    root = _write_record_root(
        tmp_path,
        payload=_record_payload(status="candidate_set_consensus_bad", passed=False),
    )

    report = build_report(
        record_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_status" in failed
    assert "source_passed" in failed


def test_nonpromotion_closeout_review_rejects_unrecorded_source(tmp_path: Path) -> None:
    root = _write_record_root(tmp_path, payload=_record_payload(recorded=False))

    report = build_report(
        record_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_recorded" in report["final_decision"]["failed_checks"]


def test_nonpromotion_closeout_review_rejects_blocked_action(tmp_path: Path) -> None:
    root = _write_record_root(tmp_path, payload=_record_payload(blocked_action=True))

    report = build_report(
        record_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_nonpromotion_closeout_review_markdown_boundaries(tmp_path: Path) -> None:
    root = _write_record_root(tmp_path)
    report = build_report(
        record_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    markdown = render_markdown(report)

    assert "Non-Promotion Closeout Review" in markdown
    assert "Closeout complete: `True`" in markdown
    assert "plan-only" in markdown
    assert "formal seeds" in markdown
    assert "DP modification" in markdown
    assert "classical Benders" in markdown


def test_nonpromotion_closeout_review_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _write_record_root(tmp_path)
    output_json = tmp_path / "review.json"
    output_md = tmp_path / "review.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "nonpromotion-closeout-review",
            "--record_root",
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
    assert "Non-Promotion Closeout Review" in output_md.read_text(encoding="utf-8")
