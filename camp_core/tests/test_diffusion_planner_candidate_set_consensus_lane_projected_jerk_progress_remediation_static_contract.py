from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_broader_nonformal_materiality import (
    EXPECTED_DP_HEAD,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_failure_attribution import (
    EXIT_CODE,
    HEADS,
    SHA256SUMS,
)
from scripts.integrations.plan_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_remediation_design import (
    AUTHORIZED_NEXT_WORK as DESIGN_AUTHORIZED_NEXT_WORK,
    READY_STATUS as DESIGN_READY_STATUS,
)
from scripts.integrations.review_diffusion_planner_candidate_set_consensus_lane_projected_jerk_progress_remediation_static_contract import (
    AUTHORIZED_NEXT_WORK,
    DESIGN_JSON,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


def _design_payload(
    *,
    status: str = DESIGN_READY_STATUS,
    authorized_next_work: str | None = DESIGN_AUTHORIZED_NEXT_WORK,
    threads: list[str] | None = None,
) -> dict:
    thread_names = threads or [
        "relative_comfort_contract",
        "hard_feasibility_contract",
        "latency_contract",
    ]
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
        "remediation_design": {
            "selected_next_work": DESIGN_AUTHORIZED_NEXT_WORK,
            "remediation_threads": [{"name": name} for name in thread_names],
            "next_gate_checks": [
                "read-only source inspection only",
                "no candidate generation or fixed-screen rerun",
            ],
        },
    }


def _source_text() -> str:
    return """
class RouteTopologyCandidateConfig:
    generator_policy = "lane_centerline_red_stop"
    progress_loss_budgets_m = (0.5, 1.0, 1.5)
    smoothness_loss_budgets = (0.0, 0.5, 1.0)
    command_jerk_worse_budget_mps3 = 0.0
    command_lateral_worse_budget_mps2 = 0.0
    rollout_jerk_worse_budget_mps3 = 0.0
    rollout_lateral_worse_budget_mps2 = 0.0

def parse_args():
    choices=("lane_projected_jerk_progress_red_stop",)
    default="lane_centerline_red_stop"

def reward_hard_feasibility(): pass
hard_reasons = []
hard_reason_counts = {}
hard_feasible = True
route_topology_hard_feasible_but_underprogress = "route_topology_hard_feasible_but_underprogress"

def _comfort_admissible(): pass
def _comfort_failure_classes(): pass
def _validate_config(): pass
def _summarize_latency(): pass

def timing():
    time.perf_counter()
    x = "candidate_build"
    y = "total"
    candidate_build = 1
"""


def _write_sha256sums(root: Path, names: list[str]) -> None:
    lines = []
    for name in names:
        data = (root / name).read_bytes()
        lines.append(f"{hashlib.sha256(data).hexdigest()}  {name}")
    (root / SHA256SUMS).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_design_root(tmp_path: Path, payload: dict | None = None) -> Path:
    root = tmp_path / "design"
    root.mkdir()
    (root / DESIGN_JSON).write_text(
        json.dumps(payload or _design_payload(), indent=2) + "\n",
        encoding="utf-8",
    )
    (root / EXIT_CODE).write_text("0\n", encoding="utf-8")
    (root / HEADS).write_text("HEADS\n", encoding="utf-8")
    _write_sha256sums(root, [DESIGN_JSON, EXIT_CODE, HEADS])
    return root


def _write_source(tmp_path: Path, text: str | None = None) -> Path:
    path = tmp_path / "analyze_diffusion_planner_route_topology_candidate_screen.py"
    path.write_text(text or _source_text(), encoding="utf-8")
    return path


def _build(
    tmp_path: Path,
    *,
    payload: dict | None = None,
    source_text: str | None = None,
) -> dict:
    design_root = _write_design_root(tmp_path, payload)
    source_path = _write_source(tmp_path, source_text)
    return build_report(
        design_root=design_root,
        source_path=source_path,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )


def test_static_contract_review_complete(tmp_path: Path) -> None:
    report = _build(tmp_path)

    decision = report["final_decision"]
    review = report["static_contract_review"]
    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["candidate_generation_execution_authorized"] is False
    assert decision["fixed_snapshot_screen_rerun_authorized"] is False
    assert decision["new_replay_authorized"] is False
    assert review["selected_next_work"] == AUTHORIZED_NEXT_WORK
    assert [item["name"] for item in review["contracts"]] == [
        "relative_comfort_contract",
        "hard_feasibility_contract",
        "latency_contract",
        "policy_default_off_contract",
    ]


def test_static_contract_review_rejects_sha_mismatch(tmp_path: Path) -> None:
    design_root = _write_design_root(tmp_path)
    source_path = _write_source(tmp_path)
    (design_root / DESIGN_JSON).write_text("{}", encoding="utf-8")

    report = build_report(
        design_root=design_root,
        source_path=source_path,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head=EXPECTED_DP_HEAD,
        label="unit",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "design_sha256sums_ok" in report["final_decision"]["failed_checks"]


def test_static_contract_review_rejects_dp_mismatch(tmp_path: Path) -> None:
    design_root = _write_design_root(tmp_path)
    source_path = _write_source(tmp_path)

    report = build_report(
        design_root=design_root,
        source_path=source_path,
        camp_head="abc",
        camp_origin_main="abc",
        dp_head="wrong",
        label="unit",
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_static_contract_review_rejects_missing_design_authorization(
    tmp_path: Path,
) -> None:
    payload = _design_payload(authorized_next_work="not_allowed")
    report = _build(tmp_path, payload=payload)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "design_authorizes_static_contract_review" in report["final_decision"][
        "failed_checks"
    ]


def test_static_contract_review_rejects_missing_design_thread(tmp_path: Path) -> None:
    payload = _design_payload(threads=["relative_comfort_contract"])
    report = _build(tmp_path, payload=payload)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "design_threads_present" in report["final_decision"]["failed_checks"]


def test_static_contract_review_rejects_missing_source_token(tmp_path: Path) -> None:
    source = _source_text().replace("_comfort_admissible", "missing_comfort")
    report = _build(tmp_path, source_text=source)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "contract_relative_comfort_contract_present" in report["final_decision"][
        "failed_checks"
    ]


def test_static_contract_review_markdown_boundaries(tmp_path: Path) -> None:
    report = _build(tmp_path)
    markdown = render_markdown(report)

    assert "Static Contract Review" in markdown
    assert "relative_comfort_contract" in markdown
    assert "source edits are not authorized" in markdown
    assert "candidate generation execution is not authorized" in markdown
    assert "fixed-snapshot screen rerun is not authorized" in markdown
    assert "replay is not authorized" in markdown
    assert "formal seeds 11/12/13 remain frozen" in markdown
    assert "DP weights and DP code must remain fixed" in markdown
    assert "classical Benders" in markdown


def test_static_contract_review_cli_writes_outputs(tmp_path: Path, monkeypatch) -> None:
    design_root = _write_design_root(tmp_path)
    source_path = _write_source(tmp_path)
    output_json = tmp_path / "out" / "review.json"
    output_md = tmp_path / "out" / "review.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "review",
            "--design_root",
            str(design_root),
            "--source_path",
            str(source_path),
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
        "# Lane-Projected Jerk/Progress Remediation Static Contract Review"
    )
