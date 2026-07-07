#!/usr/bin/env python3
"""Preflight the v15 broader non-formal evidence expansion plan."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
SCHEMA_VERSION = "dp_camp_v15_broader_nonformal_evidence_expansion_plan_preflight_v1"
AUTHORIZED_CURRENT_WORK = "v15_broader_nonformal_evidence_expansion_plan_preflight"
READY_STATUS = "v15_broader_nonformal_evidence_expansion_plan_preflight_ready"
REJECT_STATUS = "v15_broader_nonformal_evidence_expansion_plan_preflight_rejected"
AUTHORIZED_NEXT_WORK = "v15_broader_nonformal_evidence_expansion_plan_preflight_static_review_only"
REPORT_JSON_NAME = "v15_broader_nonformal_evidence_expansion_plan_preflight.json"
REPORT_MD_NAME = "v15_broader_nonformal_evidence_expansion_plan_preflight.md"

FORMAL_SEEDS = {11, 12, 13}
SCENARIO_BUCKETS = (
    "normal",
    "traffic_light",
    "red_light_turn",
    "sharp_turn",
    "npc_interaction",
    "dense_scene",
    "lane_change_or_merge",
)
NONFORMAL_MATRIX = {
    "routes": (
        "sample_normal",
        "sample_tl",
        "nishi_release",
        "nishi_lane_change",
        "left_turn_red_light",
        "sharp_turn",
        "dense_merge",
        "npc_interaction",
    ),
    "train_seeds": (2100, 2101, 2102, 2103),
    "calibration_seeds": (2104, 2105),
    "holdout_seeds": (2106, 2107),
    "npc_modes": ("none", "single", "dense"),
    "traffic_light_modes": ("off", "green", "red"),
}
ARTIFACT_LAYOUT = (
    "HEADS",
    "COMMAND",
    "stdout.txt",
    "stderr.txt",
    "run.exit",
    REPORT_JSON_NAME,
    REPORT_MD_NAME,
    "timing.json",
    "timing.md",
    "SHA256SUMS",
)
NO_GO_CONDITIONS = (
    "full36_scope_requested",
    "formal_seed_11_12_13_used",
    "full36_or_formal_result_used_for_training_calibration_or_online_input",
    "dp_head_drift",
    "dp_code_config_weight_or_checkpoint_modified",
    "camp_candidate_tensor_or_trajectory_mutation",
    "reference_blend_guidance_postprocess_or_postselection",
    "closed_loop_outcome_used_for_training_or_online_selector_input",
    "non_affine_score_or_non_simplex_weights",
    "nonconvex_simplex_cvar_l2_master",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v14_audit_md", type=Path, required=True)
    parser.add_argument("--current_status_md", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument(
        "--enable_v15_broader_nonformal_evidence_expansion_plan_preflight",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        v14_audit_md=args.v14_audit_md,
        current_status_md=args.current_status_md,
        output_dir=args.output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        enabled=args.enable_v15_broader_nonformal_evidence_expansion_plan_preflight,
    )
    write_outputs(args.output_dir, report)
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    v14_audit_md: Path,
    current_status_md: Path,
    output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    enabled: bool = False,
    matrix: dict[str, tuple[Any, ...]] | None = None,
) -> dict[str, Any]:
    selected_matrix = matrix or NONFORMAL_MATRIX
    v14_text = v14_audit_md.read_text(encoding="utf-8")
    status_text = current_status_md.read_text(encoding="utf-8")

    checks = [
        _expect("preflight_enabled", enabled, True),
        _expect("camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("dp_head_fixed", current_dp_head, required_dp_head),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("camp_head_is_sha", _is_sha(current_camp_head), current_camp_head, "40-char sha"),
        _check("origin_main_is_sha", _is_sha(current_camp_origin_main), current_camp_origin_main, "40-char sha"),
        _check("v14_audit_exists", v14_audit_md.is_file(), str(v14_audit_md), "file"),
        _check("current_status_exists", current_status_md.is_file(), str(current_status_md), "file"),
        _contains("v14_audit_auditable_complete", v14_text, "auditable_integration_complete=True"),
        _contains("v14_audit_no_further_action", v14_text, "next_work_target=no_further_action_"),
        _contains("v14_audit_fixed_dp_scope", v14_text, "CAMP selector over fixed Diffusion Planner candidate tensor"),
        _contains("v14_audit_no_dp_modification", v14_text, "dp_modification=False"),
        _contains("v14_audit_no_candidate_tensor_modification", v14_text, "candidate_tensor_modification=False"),
        _contains("current_status_mentions_v15", status_text, "docs/diffusion_planner_v15_iteration_audit.md"),
        _contains("current_status_marks_v14_sealed", status_text, "v14 is sealed evidence"),
    ]
    checks.extend(_matrix_checks(selected_matrix))
    checks.extend(_scenario_bucket_checks())
    checks.extend(_artifact_layout_checks())

    failed = [check["name"] for check in checks if not check["passed"]]
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": READY_STATUS if not failed else REJECT_STATUS,
        "authorized_current_work": AUTHORIZED_CURRENT_WORK,
        "authorized_next_work": AUTHORIZED_NEXT_WORK,
        "heads": {
            "camp_head": current_camp_head,
            "camp_origin_main": current_camp_origin_main,
            "dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "matrix": selected_matrix,
        "split": {
            "train": selected_matrix["train_seeds"],
            "calibration": selected_matrix["calibration_seeds"],
            "holdout": selected_matrix["holdout_seeds"],
            "zero_overlap_keys": (
                "route",
                "seed",
                "npc_mode",
                "traffic_light_mode",
                "candidate_tensor_sha256",
                "record_id",
            ),
        },
        "fixed_dp_candidate_tensor_provenance": {
            "dp_head": FIXED_DP_HEAD,
            "camp_action": "rerank_or_select_only",
            "candidate_generation_by_camp": False,
            "candidate_tensor_modification": False,
            "trajectory_modification": False,
        },
        "paired_protocol": {
            "comparison": "camp_selected_candidate_vs_dp_top1",
            "score": "score_k(w)=a_k^T w",
            "weights": "nonnegative_simplex_over_approved_atoms",
            "master": "convex_simplex_cvar_l2",
            "scenario_buckets": SCENARIO_BUCKETS,
        },
        "pass_fail_criteria": {
            "primary": "holdout paired SafetyCost_v1 delta improves with CI95 high < 0",
            "required": (
                "zero overlap passes",
                "fixed DP tensor provenance passes",
                "no formal seeds or Full36 inputs",
                "no DP or trajectory mutation",
                "timing artifact complete",
            ),
        },
        "timing_requirements": {
            "offline_training": (
                "wall_clock_seconds",
                "start_timestamp",
                "end_timestamp",
                "training_command",
                "training_sample_count",
                "artifact_model_config_log_sha256",
            ),
            "online_selector_latency": ("count", "mean", "median", "p95", "p99", "max"),
            "fallback_latency": ("count", "mean", "median", "p95", "p99", "max"),
            "artifact_files": ("timing.json", "timing.md", "SHA256SUMS"),
            "instrumentation_changes_selector_behavior": False,
            "gpu_model_required": False,
        },
        "no_go_conditions": NO_GO_CONDITIONS,
        "artifact_layout": ARTIFACT_LAYOUT,
        "checks": checks,
        "final_decision": {
            "passed": not failed,
            "status": READY_STATUS if not failed else REJECT_STATUS,
            "failed_checks": failed,
            "check_count": len(checks),
            "authorized_next_work": AUTHORIZED_NEXT_WORK if not failed else None,
            "training_executed": False,
            "paired_evaluation_executed": False,
            "full36_used": False,
            "formal_seed_11_12_13_used": False,
            "dp_modified": False,
            "candidate_tensor_modified": False,
            "trajectory_modified": False,
            "camp_action": "rerank_or_select_only",
        },
    }
    return _stable(report)


def write_outputs(output_dir: Path, report: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / REPORT_JSON_NAME
    md_path = output_dir / REPORT_MD_NAME
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(report), encoding="utf-8")
    sha_path = output_dir / "SHA256SUMS"
    sha_path.write_text(
        "\n".join(
            f"{_sha256(path)}  {path.name}"
            for path in (json_path, md_path)
        )
        + "\n",
        encoding="utf-8",
    )


def _render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# V15 Broader Non-Formal Evidence Expansion Plan Preflight",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- DP head: `{report['heads']['dp_head']}`",
        "- Scope: CAMP rerank/select over fixed DP candidate tensors only.",
        "- Timing: offline training and online selector latency artifacts are required for later execution gates.",
        "",
        "## Scenario Buckets",
        "",
    ]
    lines.extend(f"- `{bucket}`" for bucket in SCENARIO_BUCKETS)
    lines.extend(["", "## No-Go Conditions", ""])
    lines.extend(f"- `{condition}`" for condition in NO_GO_CONDITIONS)
    lines.extend(["", "## Artifact Layout", ""])
    lines.extend(f"- `{name}`" for name in ARTIFACT_LAYOUT)
    lines.append("")
    return "\n".join(lines)


def _matrix_checks(matrix: dict[str, tuple[Any, ...]]) -> list[dict[str, Any]]:
    all_seeds = tuple(matrix["train_seeds"] + matrix["calibration_seeds"] + matrix["holdout_seeds"])
    return [
        _check("matrix_has_routes", len(matrix["routes"]) >= 8, len(matrix["routes"]), ">=8"),
        _check("matrix_has_train_calibration_holdout", all(len(matrix[key]) > 0 for key in ("train_seeds", "calibration_seeds", "holdout_seeds")), matrix, "non-empty splits"),
        _check("matrix_has_npc_modes", len(matrix["npc_modes"]) >= 3, matrix["npc_modes"], ">=3 modes"),
        _check("matrix_has_traffic_light_modes", len(matrix["traffic_light_modes"]) >= 3, matrix["traffic_light_modes"], ">=3 modes"),
        _check("matrix_split_seeds_unique", len(set(all_seeds)) == len(all_seeds), all_seeds, "unique seeds"),
        _check("matrix_no_formal_seeds", not (set(all_seeds) & FORMAL_SEEDS), all_seeds, "no 11/12/13"),
    ]


def _scenario_bucket_checks() -> list[dict[str, Any]]:
    return [_check(f"scenario_bucket_{bucket}", bucket in SCENARIO_BUCKETS, bucket, "present") for bucket in SCENARIO_BUCKETS]


def _artifact_layout_checks() -> list[dict[str, Any]]:
    required = {"HEADS", "COMMAND", "stdout.txt", "stderr.txt", "run.exit", REPORT_JSON_NAME, REPORT_MD_NAME, "timing.json", "timing.md", "SHA256SUMS"}
    return [_check("artifact_layout_complete", required.issubset(set(ARTIFACT_LAYOUT)), ARTIFACT_LAYOUT, sorted(required))]


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, needle if needle in text else "missing", needle)


def _expect(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return _check(name, actual == expected, actual, expected)


def _check(name: str, passed: bool, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "actual": actual, "expected": expected}


def _is_sha(value: str) -> bool:
    return len(value) == 40 and all(char in "0123456789abcdef" for char in value)


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, tuple):
        return [_stable(item) for item in value]
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
