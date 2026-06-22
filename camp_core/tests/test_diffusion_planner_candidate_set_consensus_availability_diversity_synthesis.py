from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_availability_diversity_synthesis import (
    AUTHORIZED_NEXT_WORK,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_post_nonpromotion_next_gate import (
    AUTHORIZED_NEXT_WORK as SOURCE_AUTHORIZED_NEXT_WORK,
    READY_STATUS as SOURCE_READY_STATUS,
)


POST_JSON = "candidate_set_consensus_post_nonpromotion_next_gate_plan.json"
POST_MD = "candidate_set_consensus_post_nonpromotion_next_gate_plan.md"


def _write_sha256sums(root: Path, names: tuple[str, ...]) -> None:
    lines = []
    for name in names:
        digest = hashlib.sha256((root / name).read_bytes()).hexdigest()
        lines.append(f"{digest}  {name}")
    (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _post_plan_payload(*, status: str = SOURCE_READY_STATUS, passed: bool = True) -> dict[str, object]:
    return {
        "final_decision": {
            "status": status,
            "passed": passed,
            "authorized_next_work": SOURCE_AUTHORIZED_NEXT_WORK,
            "post_nonpromotion_next_gate_plan_ready": passed,
            "candidate_availability_diversity_synthesis_plan_authorized": passed,
            "selected_next_work": SOURCE_AUTHORIZED_NEXT_WORK,
            "safety_benefit_evidence": False,
            "atom_promotion_authorized": False,
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
        "next_gate_plan": {
            "selected_next_work": SOURCE_AUTHORIZED_NEXT_WORK,
            "broader_replay_consideration_status": "already_completed_not_reopened",
            "safety_score_atom_branch_status": "closed_nonpromotion_not_reopened",
        },
    }


def _write_post_plan_root(
    tmp_path: Path,
    *,
    payload: dict[str, object] | None = None,
    exit_code: str = "0",
) -> Path:
    root = tmp_path / "post_plan"
    root.mkdir()
    (root / POST_JSON).write_text(
        json.dumps(payload or _post_plan_payload()),
        encoding="utf-8",
    )
    (root / POST_MD).write_text("# post plan\n", encoding="utf-8")
    (root / "COMMAND.log").write_text("command\n", encoding="utf-8")
    (root / "COMMAND.err").write_text("", encoding="utf-8")
    (root / "EXIT_CODE").write_text(f"{exit_code}\n", encoding="utf-8")
    (root / "HEADS.txt").write_text(
        f"CAMP_HEAD=head\nDP_HEAD={EXPECTED_DP_HEAD}\n",
        encoding="utf-8",
    )
    _write_sha256sums(
        root,
        (POST_JSON, POST_MD, "COMMAND.log", "COMMAND.err", "EXIT_CODE", "HEADS.txt"),
    )
    return root


def _decision(status: str, **extra: object) -> dict[str, object]:
    decision: dict[str, object] = {"status": status}
    decision.update(extra)
    return {"final_decision": decision}


def _write_evidence(tmp_path: Path, overrides: dict[str, dict[str, object]] | None = None) -> dict[str, Path]:
    payloads = {
        "support_bottleneck": _decision(
            "current_fixed_dp_selector_calibration_exhausted",
        ),
        "next_design_preflight": _decision(
            "next_design_preflight_has_conditional_paths",
            conditional_paths=["new_mode_seeking_candidate_generation"],
        ),
        "mode_seeking_gate": _decision(
            "mode_seeking_candidate_design_gate_ready",
        ),
        "old_guidance_availability": _decision(
            "mode_seeking_candidate_availability_rejected",
            gates={"candidate0_preserved": False},
        ),
        "dense_guidance_availability": _decision(
            "mode_seeking_candidate_availability_rejected",
            gates={"candidate0_preserved": True, "latency_p95_pass": False},
        ),
        "dense_guidance_failure_source": _decision(
            "mode_seeking_failure_source_candidate_support_insufficient",
            reward_gate_suspect=False,
            geometry_or_tracker_support_insufficient=True,
            latency_blocked=True,
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


def test_availability_diversity_synthesis_plan_ready(tmp_path: Path) -> None:
    post_root = _write_post_plan_root(tmp_path)
    evidence_paths = _write_evidence(tmp_path)

    report = build_report(
        post_plan_root=post_root,
        evidence_paths=evidence_paths,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )
    decision = report["final_decision"]
    synthesis = report["synthesis_plan"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["candidate_availability_diversity_synthesis_plan_ready"] is True
    assert decision["candidate_generation_support_redesign_plan_authorized"] is True
    assert synthesis["selection_type"] == "fresh_plan_only_gate"
    assert synthesis["selected_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["new_replay_authorized"] is False
    assert decision["dp_modification_authorized"] is False


def test_availability_diversity_synthesis_rejects_post_plan_sha_mismatch(
    tmp_path: Path,
) -> None:
    post_root = _write_post_plan_root(tmp_path)
    (post_root / POST_MD).write_text("# mutated\n", encoding="utf-8")

    report = build_report(
        post_plan_root=post_root,
        evidence_paths=_write_evidence(tmp_path),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "post_plan_sha256sums_ok" in report["final_decision"]["failed_checks"]


def test_availability_diversity_synthesis_rejects_dp_mismatch(tmp_path: Path) -> None:
    report = build_report(
        post_plan_root=_write_post_plan_root(tmp_path),
        evidence_paths=_write_evidence(tmp_path),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head="wrong",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_availability_diversity_synthesis_rejects_source_not_ready(
    tmp_path: Path,
) -> None:
    post_root = _write_post_plan_root(
        tmp_path,
        payload=_post_plan_payload(status="candidate_set_consensus_bad", passed=False),
    )

    report = build_report(
        post_plan_root=post_root,
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


def test_availability_diversity_synthesis_rejects_wrong_evidence_status(
    tmp_path: Path,
) -> None:
    report = build_report(
        post_plan_root=_write_post_plan_root(tmp_path),
        evidence_paths=_write_evidence(
            tmp_path,
            {
                "mode_seeking_gate": _decision("unexpected_ready"),
            },
        ),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "evidence_mode_seeking_gate_status" in report["final_decision"]["failed_checks"]


def test_availability_diversity_synthesis_rejects_reward_gate_only_failure(
    tmp_path: Path,
) -> None:
    report = build_report(
        post_plan_root=_write_post_plan_root(tmp_path),
        evidence_paths=_write_evidence(
            tmp_path,
            {
                "dense_guidance_failure_source": _decision(
                    "mode_seeking_failure_source_candidate_support_insufficient",
                    reward_gate_suspect=True,
                    geometry_or_tracker_support_insufficient=True,
                    latency_blocked=True,
                ),
            },
        ),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "failure_source_not_reward_gate_only" in report["final_decision"]["failed_checks"]


def test_availability_diversity_synthesis_markdown_boundaries(tmp_path: Path) -> None:
    report = build_report(
        post_plan_root=_write_post_plan_root(tmp_path),
        evidence_paths=_write_evidence(tmp_path),
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
    )

    markdown = render_markdown(report)

    assert "Availability/Diversity Synthesis Plan" in markdown
    assert "plan-only" in markdown
    assert "no replay" in markdown
    assert "no candidate generation execution" in markdown
    assert "formal seeds" in markdown
    assert "DP weights and DP code must remain fixed" in markdown
    assert "classical Benders" in markdown


def test_availability_diversity_synthesis_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    post_root = _write_post_plan_root(tmp_path)
    evidence_paths = _write_evidence(tmp_path)
    output_json = tmp_path / "synthesis.json"
    output_md = tmp_path / "synthesis.md"
    evidence_args = [
        item
        for name, path in sorted(evidence_paths.items())
        for item in ("--evidence_json", f"{name}={path}")
    ]
    monkeypatch.setattr(
        "sys.argv",
        [
            "availability-diversity-synthesis",
            "--post_plan_root",
            str(post_root),
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
    assert "Availability/Diversity Synthesis Plan" in output_md.read_text(encoding="utf-8")
