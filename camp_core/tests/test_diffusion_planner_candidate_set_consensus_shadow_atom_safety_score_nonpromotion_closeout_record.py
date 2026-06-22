from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.record_diffusion_planner_candidate_set_consensus_shadow_atom_safety_score_nonpromotion_closeout import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


AUTH_JSON = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_authorization.json"
)
AUTH_MD = (
    "candidate_set_consensus_shadow_atom_safety_score_"
    "nonpromotion_closeout_authorization.md"
)


def _write_sha256sums(root: Path, names: tuple[str, ...]) -> None:
    lines = []
    for name in names:
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _authorization_payload(
    *,
    status: str = (
        "candidate_set_consensus_shadow_atom_safety_score_"
        "nonpromotion_closeout_authorization_ready"
    ),
    passed: bool = True,
    blocked_action: bool = False,
    recorded: bool = False,
) -> dict[str, object]:
    return {
        "final_decision": {
            "status": status,
            "passed": passed,
            "authorized_next_work": (
                "candidate_set_consensus_shadow_atom_safety_score_"
                "nonpromotion_closeout_record_only"
            ),
            "nonpromotion_closeout_authorization_ready": passed,
            "nonpromotion_closeout_record_authorized": passed,
            "nonpromotion_closeout_recorded": recorded,
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
        "plan_summary": {
            "closeout_decision": "do_not_promote_shadow_atom_keep_default_off",
            "default_off_retained": True,
            "promotion_blockers": [
                "safety_benefit_evidence remains false",
                "formal seeds 11/12/13 remain frozen and unused",
            ],
            "required_closeout_records": [
                "candidate-set consensus safety-score atom remains shadow-only/default-off",
                "no CAMP retraining, online selector promotion, Full36, formal seeds, replay, or DP modification is authorized",
            ],
        },
    }


def _write_authorization_root(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
    exit_code: str = "0",
) -> Path:
    root = tmp_path / "authorization"
    root.mkdir()
    (root / AUTH_JSON).write_text(
        json.dumps(payload or _authorization_payload()),
        encoding="utf-8",
    )
    (root / AUTH_MD).write_text("# authorization\n", encoding="utf-8")
    (root / "COMMAND.log").write_text("command\n", encoding="utf-8")
    (root / "COMMAND.err").write_text("", encoding="utf-8")
    (root / "EXIT_CODE").write_text(f"{exit_code}\n", encoding="utf-8")
    (root / "HEADS.txt").write_text(
        f"CAMP_HEAD=head\nDP_HEAD={EXPECTED_DP_HEAD}\n",
        encoding="utf-8",
    )
    _write_sha256sums(
        root,
        (AUTH_JSON, AUTH_MD, "COMMAND.log", "COMMAND.err", "EXIT_CODE", "HEADS.txt"),
    )
    return root


def test_nonpromotion_closeout_record_ready(tmp_path: Path) -> None:
    root = _write_authorization_root(tmp_path)

    report = build_report(
        authorization_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["nonpromotion_closeout_record_ready"] is True
    assert decision["nonpromotion_closeout_recorded"] is True
    assert decision["nonpromotion_closeout_review_authorized"] is True
    assert decision["safety_benefit_evidence"] is False
    assert decision["atom_promotion_authorized"] is False
    assert report["closeout_record"]["final_atom_state"] == "shadow_only_default_off_not_promoted"


def test_nonpromotion_closeout_record_rejects_sha_mismatch(tmp_path: Path) -> None:
    root = _write_authorization_root(tmp_path)
    (root / AUTH_MD).write_text("# mutated\n", encoding="utf-8")

    report = build_report(
        authorization_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "authorization_sha256sums_ok" in report["final_decision"]["failed_checks"]


def test_nonpromotion_closeout_record_rejects_dp_mismatch(tmp_path: Path) -> None:
    root = _write_authorization_root(tmp_path)

    report = build_report(
        authorization_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head="wrong",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_nonpromotion_closeout_record_rejects_source_not_ready(tmp_path: Path) -> None:
    root = _write_authorization_root(
        tmp_path,
        payload=_authorization_payload(status="candidate_set_consensus_bad", passed=False),
    )

    report = build_report(
        authorization_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    failed = report["final_decision"]["failed_checks"]
    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_status" in failed
    assert "source_passed" in failed
    assert report["final_decision"]["authorized_next_work"] is None


def test_nonpromotion_closeout_record_rejects_blocked_action(tmp_path: Path) -> None:
    root = _write_authorization_root(
        tmp_path,
        payload=_authorization_payload(blocked_action=True),
    )

    report = build_report(
        authorization_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_no_blocked_actions" in report["final_decision"]["failed_checks"]


def test_nonpromotion_closeout_record_rejects_already_recorded_source(
    tmp_path: Path,
) -> None:
    root = _write_authorization_root(
        tmp_path,
        payload=_authorization_payload(recorded=True),
    )

    report = build_report(
        authorization_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "source_record_not_already_written" in report["final_decision"]["failed_checks"]


def test_nonpromotion_closeout_record_markdown_boundaries(tmp_path: Path) -> None:
    root = _write_authorization_root(tmp_path)
    report = build_report(
        authorization_root=root,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    markdown = render_markdown(report)

    assert "Non-Promotion Closeout Record" in markdown
    assert "Closeout recorded: `True`" in markdown
    assert "Default-off retained: `True`" in markdown
    assert "formal seeds" in markdown
    assert "DP modification" in markdown
    assert "classical Benders" in markdown


def test_nonpromotion_closeout_record_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _write_authorization_root(tmp_path)
    output_json = tmp_path / "record.json"
    output_md = tmp_path / "record.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "nonpromotion-closeout-record",
            "--authorization_root",
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
    assert "Non-Promotion Closeout Record" in output_md.read_text(encoding="utf-8")
