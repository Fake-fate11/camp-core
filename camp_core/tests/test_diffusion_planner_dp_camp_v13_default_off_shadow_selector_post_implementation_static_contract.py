from __future__ import annotations

from pathlib import Path

import pytest

from scripts.integrations.review_diffusion_planner_dp_camp_v13_default_off_shadow_selector_post_implementation_static_contract import (
    AUTHORIZED_NEXT_WORK,
    DISABLED_STATUS,
    FIXED_DP_HEAD,
    READY_STATUS,
    REJECT_STATUS,
    build_report,
    main,
    render_markdown,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
CAMP_HEAD = "df76611dd58464ea14d91eda3034447fc91f5263"


def _runner_source(*, include_top1_override: bool = True) -> str:
    top1_override = (
        "selected_index = 0 if default_off_shadow_selector else baseline_selected_index"
        if include_top1_override
        else "selected_index = baseline_selected_index"
    )
    return f'''
DEFAULT_OFF_SHADOW_SELECTOR_SCHEMA_VERSION = "dp_camp_v13_default_off_shadow_selector_runtime_v1"
DEFAULT_OFF_SHADOW_SELECTOR_EXPECTED_K = 8
parser.add_argument("--camp_default_off_shadow_selector", action="store_true")

def _normalize_sha256(value): pass
def _load_shadow_artifact_manifest(path): pass
def _shadow_artifact_entry(): pass
def _default_off_shadow_selector_contract(args): pass
def _mark_shadow_selector_fail_closed(contract, reason): pass
def _summarize_default_off_shadow_selector_records(records): pass

entry = {{"expected_sha256": None, "actual_sha256": None, "hash_match": False}}
failed_checks = ["candidate_count_drift", "selector_artifact_load_failed"]
if args.camp_default_off_shadow_selector and not bool(contract.get("ready")):
    selector = None
if not args.camp_default_off_shadow_selector:
    raise RuntimeError("other mode")
raise ValueError("--camp_default_off_shadow_selector cannot be combined with --camp_underprogress_relaxation; shadow execution must remain DP Top-1.")
flags = [
    "--camp_perfect_tracker_command_postselection",
    "--camp_traffic_light_hybrid_postselection",
    "--camp_underprogress_relaxation",
    "--camp_splice_shadow_rule",
]
shadow_selected_index = (
            baseline_selected_index if default_off_shadow_selector else None
)
{top1_override}
selected_trajectory = candidates[selected_index]
record = {{
    "selected_index": selected_index,
    "executed_index": selected_index,
    "shadow_selected_index": shadow_selected_index,
    "executed_output_policy": "dp_top1",
    "selection_effect": False,
    "score_expression": "score_k(w)=a_k^T w",
}}
summary = {{"camp_default_off_shadow_selector": camp_default_off_shadow_selector}}
validation["camp_default_off_shadow_selector"] = camp_default_off_shadow_selector
'''


def _unit_test_source(*, include_runtime_test: bool = True) -> str:
    runtime_test = (
        "def test_dp_top1_shadow_runtime_contract_never_routes_shadow_argmin(): pass"
        if include_runtime_test
        else ""
    )
    return f'''
def test_default_off_disabled_contract_returns_dp_top1_before_artifact_reads(): pass
def test_immutable_artifact_hash_contract_fails_closed_on_mismatch(): pass
def test_fixed_candidate_affine_score_contract_uses_k8_matrix_product(): pass
{runtime_test}
def test_no_candidate_mutation_contract_keeps_tensor_hash_and_shape(): pass
def test_benders_boundary_keeps_scores_affine_in_simplex_weights(): pass
def test_formal_seed_boundary_rejects_frozen_seeds_without_selection(): pass
def test_runner_shadow_contract_missing_artifacts_fail_closed(): pass
def test_runner_shadow_contract_accepts_clean_hash_manifest(): pass
def test_runner_shadow_selector_rejects_execution_changing_flags(): pass
def test_runner_shadow_summary_records_dp_top1_execution(): pass
def test_current_static_source_surfaces_preserve_rerank_boundary(): pass
'''


def _benders_source() -> str:
    return """
def test_fixed_candidate_atom_scores_are_affine_in_simplex_weights(): pass
def test_robust_margin_master_rejects_negative_atom_coefficients(): pass
"""


def _audit_source() -> str:
    return """
current_v13_status=default_off_shadow_selector_implementation_complete
v13_default_off_shadow_selector_post_implementation_static_contract_review_authorized=True
next_work_target=dp_camp_v13_default_off_shadow_selector_post_implementation_static_contract_review_only
v13_default_off_shadow_selector_runtime_default_off=True
v13_default_off_shadow_selector_runtime_effect=records shadow_selected_index while selected_index and executed_index remain DP candidate 0
v13_default_off_shadow_selector_runtime_incompatible_flags_rejected=camp_perfect_tracker_command_postselection,camp_traffic_light_hybrid_postselection,camp_underprogress_relaxation,camp_splice_shadow_rule
v13_default_off_shadow_selector_score_expression=score_k(w)=a_k^T w
online_selector_change_authorized=False
executed_trajectory_change_authorized=False
candidate_generation_authorized_by_current_boundary=False
current_v13_training_authorized_by_user=True
"""


def _write_inputs(
    tmp_path: Path,
    *,
    include_top1_override: bool = True,
    include_runtime_test: bool = True,
) -> dict[str, Path]:
    paths = {
        "replay_runner_py": tmp_path / "runner.py",
        "shadow_unit_test_py": tmp_path / "test_shadow.py",
        "benders_contract_test_py": tmp_path / "test_benders.py",
        "v13_audit_md": tmp_path / "audit.md",
    }
    paths["replay_runner_py"].write_text(
        _runner_source(include_top1_override=include_top1_override),
        encoding="utf-8",
    )
    paths["shadow_unit_test_py"].write_text(
        _unit_test_source(include_runtime_test=include_runtime_test),
        encoding="utf-8",
    )
    paths["benders_contract_test_py"].write_text(_benders_source(), encoding="utf-8")
    paths["v13_audit_md"].write_text(_audit_source(), encoding="utf-8")
    return paths


def _build(tmp_path: Path, **kwargs) -> dict:
    return build_report(
        **_write_inputs(tmp_path, **kwargs),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=True,
    )


def test_post_implementation_static_contract_is_default_off(tmp_path: Path) -> None:
    missing = tmp_path / "missing.py"
    report = build_report(
        replay_runner_py=missing,
        shadow_unit_test_py=missing,
        benders_contract_test_py=missing,
        v13_audit_md=missing,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=False,
    )

    assert report["final_decision"]["status"] == DISABLED_STATUS
    assert report["review_checks"] == []


def test_post_implementation_static_contract_ready(tmp_path: Path) -> None:
    report = _build(tmp_path)
    decision = report["final_decision"]

    assert decision["status"] == READY_STATUS
    assert decision["authorized_next_work"] == AUTHORIZED_NEXT_WORK
    assert decision["post_implementation_static_contract_review_complete"] is True
    assert decision["artifact_manifest_plan_authorized"] is True
    assert decision["artifact_manifest_materialization_authorized"] is False
    assert decision["default_off_shadow_selector_runtime_execution_authorized"] is False
    assert decision["selector_promotion_authorized"] is False
    assert decision["deployment_authorized"] is False
    assert report["contract_summary"]["dp_top1_override_present"] is True
    assert report["contract_summary"]["artifact_hash_contract_present"] is True


def test_current_repo_post_implementation_static_contract_passes() -> None:
    report = build_report(
        replay_runner_py=REPO_ROOT
        / "scripts"
        / "integrations"
        / "run_diffusion_planner_camp_replay.py",
        shadow_unit_test_py=REPO_ROOT
        / "camp_core"
        / "tests"
        / "test_diffusion_planner_dp_camp_v13_default_off_shadow_selector_implementation_unit_tests.py",
        benders_contract_test_py=REPO_ROOT
        / "camp_core"
        / "tests"
        / "test_diffusion_planner_benders_atom_contract.py",
        v13_audit_md=REPO_ROOT / "docs" / "diffusion_planner_v13_iteration_audit.md",
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["failed_checks"] == []


def test_post_implementation_static_contract_rejects_missing_top1_override(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, include_top1_override=False)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "runner_dp_top1_execution_override" in report["final_decision"][
        "failed_checks"
    ]


def test_post_implementation_static_contract_rejects_missing_runtime_test(
    tmp_path: Path,
) -> None:
    report = _build(tmp_path, include_runtime_test=False)

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "unit_dp_top1_runtime_contract" in report["final_decision"][
        "failed_checks"
    ]


def test_post_implementation_static_contract_rejects_dp_mismatch(
    tmp_path: Path,
) -> None:
    report = build_report(
        **_write_inputs(tmp_path),
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head="0" * 40,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "current_dp_head_fixed" in report["final_decision"]["failed_checks"]


def test_post_implementation_static_contract_rejects_stale_audit_boundary(
    tmp_path: Path,
) -> None:
    paths = _write_inputs(tmp_path)
    paths["v13_audit_md"].write_text(
        (
            "# Audit\n"
            "\n"
            "## Current V13 Old Implementation Boundary\n"
            "\n"
            f"{_audit_source()}\n"
            "\n"
            "## Current V13 Current Unit Tests Boundary\n"
            "\n"
            "current_v13_status=current_source_default_off_shadow_selector_implementation_unit_tests_only_complete\n"
            "next_work_target=dp_camp_v13_default_off_shadow_selector_implementation_only_after_explicit_user_authorization\n"
            "online_selector_change_authorized=False\n"
            "executed_trajectory_change_authorized=False\n"
            "candidate_generation_authorized_by_current_boundary=False\n"
            "current_v13_training_authorized_by_user=True\n"
        ),
        encoding="utf-8",
    )

    report = build_report(
        **paths,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == REJECT_STATUS
    assert "audit_records_implementation_or_post_review_complete" in report[
        "final_decision"
    ]["failed_checks"]
    assert "audit_authorizes_or_completed_post_implementation_review" in report[
        "final_decision"
    ]["failed_checks"]


def test_post_implementation_static_contract_accepts_completed_current_boundary(
    tmp_path: Path,
) -> None:
    paths = _write_inputs(tmp_path)
    paths["v13_audit_md"].write_text(
        (
            "# Audit\n"
            "\n"
            "## Current V13 Completed Post Review Boundary\n"
            "\n"
            "current_v13_status=current_source_default_off_shadow_selector_post_implementation_static_contract_review_complete\n"
            "current_source_default_off_shadow_selector_post_implementation_static_contract_review_complete=True\n"
            "next_work_target=dp_camp_v13_default_off_shadow_selector_artifact_manifest_plan_only\n"
            "v13_default_off_shadow_selector_runtime_default_off=True\n"
            "v13_default_off_shadow_selector_runtime_effect=shadow_selected_index may be logged; selected_index and executed_index remain DP candidate 0\n"
            "v13_default_off_shadow_selector_runtime_incompatible_flags_rejected=camp_perfect_tracker_command_postselection,camp_traffic_light_hybrid_postselection,camp_underprogress_relaxation,camp_splice_shadow_rule\n"
            "v13_default_off_shadow_selector_score_expression=score_k(w)=a_k^T w\n"
            "online_selector_change_authorized=False\n"
            "executed_trajectory_change_authorized=False\n"
            "candidate_generation_authorized_by_current_boundary=False\n"
            "current_v13_training_authorized_by_user=True\n"
        ),
        encoding="utf-8",
    )

    report = build_report(
        **paths,
        current_camp_head=CAMP_HEAD,
        current_camp_origin_main=CAMP_HEAD,
        current_dp_head=FIXED_DP_HEAD,
        enabled=True,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["final_decision"]["failed_checks"] == []


def test_post_implementation_static_contract_markdown_boundary(
    tmp_path: Path,
) -> None:
    markdown = render_markdown(_build(tmp_path))

    assert "Post-Implementation Static Contract Review" in markdown
    assert "Artifact manifest materialization authorized: `False`" in markdown
    assert "Shadow runtime execution authorized: `False`" in markdown
    assert "score_k(w)=a_k^T w" in markdown
    assert "This review is static only" in markdown
    assert "safety/CAMP-over-DP claims" in markdown


def test_post_implementation_static_contract_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _write_inputs(tmp_path)
    output_json = tmp_path / "out" / "review.json"
    output_md = tmp_path / "out" / "review.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "review",
            "--replay_runner_py",
            str(paths["replay_runner_py"]),
            "--shadow_unit_test_py",
            str(paths["shadow_unit_test_py"]),
            "--benders_contract_test_py",
            str(paths["benders_contract_test_py"]),
            "--v13_audit_md",
            str(paths["v13_audit_md"]),
            "--current_camp_head",
            CAMP_HEAD,
            "--current_camp_origin_main",
            CAMP_HEAD,
            "--current_dp_head",
            FIXED_DP_HEAD,
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
            "--enable_v13_default_off_shadow_selector_post_implementation_static_contract_review",
        ],
    )

    assert main() == 0
    assert output_json.is_file()
    assert output_md.is_file()
    assert READY_STATUS in output_json.read_text(encoding="utf-8")
