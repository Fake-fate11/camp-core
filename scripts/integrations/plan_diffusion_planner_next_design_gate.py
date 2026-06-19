#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SUPPORT_EXHAUSTED = "current_fixed_dp_selector_calibration_exhausted"
DP_PRIOR_COMPLETION_REJECTED = "score_schema_gap_not_candidate_support_limit"
MODE_SPREAD_MIN_M = 0.25


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only next-design preflight for CAMP-on-DP after support "
            "bottleneck synthesis. It classifies candidate next routes from "
            "existing JSON artifacts and does not run DP or change CAMP."
        )
    )
    parser.add_argument("--support_bottleneck_json", type=Path, required=True)
    parser.add_argument("--dp_prior_completion_json", type=Path, default=None)
    parser.add_argument("--candidate_generation_controls_json", type=Path, default=None)
    parser.add_argument(
        "--spatial_diversity_json",
        action="append",
        default=[],
        help="Optional NAME=PATH entries for candidate spatial diversity reports.",
    )
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        support_bottleneck=_load_json(args.support_bottleneck_json),
        dp_prior_completion=(
            None
            if args.dp_prior_completion_json is None
            else _load_json(args.dp_prior_completion_json)
        ),
        candidate_generation_controls=(
            None
            if args.candidate_generation_controls_json is None
            else _load_json(args.candidate_generation_controls_json)
        ),
        spatial_diversity=_load_named_reports(args.spatial_diversity_json),
        label=args.label,
        paths={
            "support_bottleneck_json": str(args.support_bottleneck_json),
            "dp_prior_completion_json": _path_or_none(args.dp_prior_completion_json),
            "candidate_generation_controls_json": _path_or_none(
                args.candidate_generation_controls_json
            ),
            "spatial_diversity_json": list(args.spatial_diversity_json),
        },
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")


def build_report(
    *,
    support_bottleneck: dict[str, Any],
    dp_prior_completion: dict[str, Any] | None = None,
    candidate_generation_controls: dict[str, Any] | None = None,
    spatial_diversity: dict[str, dict[str, Any]] | None = None,
    label: str | None = None,
    paths: dict[str, Any] | None = None,
) -> dict[str, Any]:
    spatial_diversity = spatial_diversity or {}
    design_routes = [
        _current_descriptor_route(support_bottleneck),
        _dp_prior_completion_route(dp_prior_completion),
        _same_mode_generator_route(spatial_diversity),
        _official_guidance_route(candidate_generation_controls, spatial_diversity),
        _new_atom_schema_route(support_bottleneck),
    ]
    decision = _decision(design_routes)
    return {
        "analysis": {
            "name": "dp_camp_next_design_gate_preflight_v1",
            "label": label,
            "role": (
                "read-only preflight that classifies possible next CAMP-on-DP "
                "design routes after current selector calibration was exhausted"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "future_outcome_leakage": (
                "this report reads existing diagnostics; outcome labels remain "
                "inside those diagnostics and are not converted into runtime "
                "selector inputs"
            ),
            "math_boundary": (
                "DP stays a frozen black-box candidate generator. This preflight "
                "does not add atoms, change candidate generation, or construct a "
                "DP-side master/subproblem. Any future runtime atom must be a "
                "current-tick fixed finite-candidate quantity, nonnegative or "
                "split into nonnegative signed parts, preserving affine CAMP "
                "scores a_k^T w and the simplex/CVaR/L2 convex master. Candidate "
                "generation variants are finite candidate-set changes, not "
                "classical Benders decomposition."
            ),
            "paths": paths or {},
            "mode_spread_min_m": MODE_SPREAD_MIN_M,
        },
        "source_statuses": {
            "support_bottleneck": _decision_status(support_bottleneck),
            "dp_prior_completion": (
                None if dp_prior_completion is None else _decision_status(dp_prior_completion)
            ),
            "candidate_generation_controls": (
                None
                if candidate_generation_controls is None
                else _get(
                    candidate_generation_controls,
                    "next_gate",
                    "decision",
                )
            ),
            "spatial_diversity_reports": sorted(spatial_diversity),
        },
        "design_routes": design_routes,
        "final_decision": decision,
    }


def _current_descriptor_route(report: dict[str, Any]) -> dict[str, Any]:
    status = _decision_status(report)
    exhausted = status == SUPPORT_EXHAUSTED
    return {
        "name": "current_descriptor_threshold_or_reweighting",
        "route_type": "selector_calibration",
        "status": "rejected" if exhausted else "inconclusive",
        "mathematically_admissible": True,
        "runtime_effect": "finite-candidate selector over existing descriptors",
        "reasons": (
            ["support_bottleneck_synthesis_exhausted_current_descriptor_family"]
            if exhausted
            else ["support_bottleneck_synthesis_not_exhausted_or_missing"]
        ),
        "next_gate": (
            "do_not_continue_threshold_tuning"
            if exhausted
            else "inspect_support_bottleneck_synthesis"
        ),
    }


def _dp_prior_completion_route(report: dict[str, Any] | None) -> dict[str, Any]:
    if report is None:
        return _missing_route(
            "dp_prior_completion_atom_schema",
            "atom_schema",
            "missing_dp_prior_completion_joint_audit",
        )
    status = _decision_status(report)
    rejected = status == DP_PRIOR_COMPLETION_REJECTED
    ranked = report.get("ranked_candidates") or []
    best = ranked[0] if ranked else {}
    return {
        "name": "dp_prior_completion_atom_schema",
        "route_type": "atom_schema",
        "status": "rejected" if rejected else "inconclusive",
        "mathematically_admissible": True,
        "runtime_effect": "adds nonnegative current-tick atoms to affine CAMP score",
        "reasons": (
            ["joint_dp_prior_completion_grid_failed_comprehensive_bucket_gate"]
            if rejected
            else ["dp_prior_completion_status_not_rejected_or_missing"]
        ),
        "evidence": {
            "source_status": status,
            "best_alpha": best.get("alpha"),
            "best_beta": best.get("beta"),
            "best_bucket_failure_count": best.get("bucket_failure_count"),
            "best_passed_joint_screen": best.get("passed_joint_screen"),
            "best_safety_delta_ci95_high": best.get("safety_delta_ci95_high"),
        },
        "next_gate": (
            "do_not_promote_standalone_dp_prior_completion_schema"
            if rejected
            else "inspect_joint_atom_grid"
        ),
    }


def _same_mode_generator_route(
    spatial_reports: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    if not spatial_reports:
        return _missing_route(
            "simple_k_noise_or_same_mode_generator",
            "candidate_generation",
            "missing_spatial_diversity_reports",
        )
    summaries = {
        name: _spatial_summary(report) for name, report in spatial_reports.items()
    }
    all_low_mode = all(item["all_screens_low_mode"] for item in summaries.values())
    all_low_spread = all(item["max_endpoint_pairwise_mean_m"] < MODE_SPREAD_MIN_M for item in summaries.values())
    rejected = all_low_mode and all_low_spread
    return {
        "name": "simple_k_noise_or_same_mode_generator",
        "route_type": "candidate_generation",
        "status": "rejected" if rejected else "inconclusive",
        "mathematically_admissible": True,
        "runtime_effect": "finite candidate-set variant under fixed DP weights",
        "reasons": (
            ["spatial_diversity_reports_show_single_mode_low_endpoint_spread"]
            if rejected
            else ["spatial_diversity_reports_do_not_uniformly_reject_generator_variant"]
        ),
        "evidence": summaries,
        "next_gate": (
            "do_not_repeat_simple_k_noise_same_mode_variants"
            if rejected
            else "inspect_candidate_generation_variant"
        ),
    }


def _official_guidance_route(
    controls: dict[str, Any] | None,
    spatial_reports: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if controls is None:
        return _missing_route(
            "new_mode_seeking_candidate_generation",
            "candidate_generation",
            "missing_candidate_generation_controls",
        )
    admissibility = controls.get("admissibility") or {}
    next_gate = controls.get("next_gate") or {}
    guidance_available = bool(admissibility.get("official_guidance_available"))
    default_off = bool(admissibility.get("guidance_can_only_be_next_gate_if_default_off"))
    simple_generator_rejected = bool(spatial_reports) and _same_mode_generator_route(
        spatial_reports
    )["status"] == "rejected"
    candidate = guidance_available and default_off and simple_generator_rejected
    return {
        "name": "new_mode_seeking_candidate_generation",
        "route_type": "candidate_generation",
        "status": "conditional_next_design" if candidate else "inconclusive",
        "mathematically_admissible": True,
        "runtime_effect": "default-off finite candidate-set variant under fixed DP weights",
        "reasons": (
            [
                "official_guidance_controls_available",
                "must_be_default_off_metadata_logged",
                "simple_k_noise_variants_rejected_as_same_mode",
            ]
            if candidate
            else ["guidance_controls_or_spatial_bottleneck_evidence_missing"]
        ),
        "evidence": {
            "controls_next_gate": next_gate.get("decision"),
            "official_guidance_available": guidance_available,
            "prototype_support_available": bool(
                admissibility.get("prototype_support_available")
            ),
            "dp_source_modification_required": bool(
                admissibility.get("dp_source_modification_required")
            ),
            "camp_atom_schema_change_required": bool(
                admissibility.get("camp_atom_schema_change_required")
            ),
        },
        "next_gate": (
            "write_predeclared_mode_seeking_candidate_set_design_before_replay"
            if candidate
            else "inspect_candidate_generation_controls"
        ),
    }


def _new_atom_schema_route(report: dict[str, Any]) -> dict[str, Any]:
    status = _decision_status(report)
    exhausted = status == SUPPORT_EXHAUSTED
    return {
        "name": "materially_new_no_leak_atom_schema",
        "route_type": "atom_schema",
        "status": "conditional_next_design" if exhausted else "inconclusive",
        "mathematically_admissible": True,
        "runtime_effect": "new nonnegative current-tick atoms before any training",
        "reasons": (
            [
                "current_descriptor_family_exhausted",
                "new_atom_must_not_be_threshold_variant_of_rejected_descriptors",
            ]
            if exhausted
            else ["support_synthesis_missing_or_not_exhausted"]
        ),
        "requirements": [
            "prove current-tick finite-candidate availability",
            "define nonnegative base costs or nonnegative signed splits",
            "keep score affine a_k^T w",
            "keep simplex/CVaR/L2 master convex",
            "audit offline before CAMP retraining",
        ],
        "next_gate": (
            "write_math_definition_then_predeclare_offline_atom_audit"
            if exhausted
            else "inspect_support_bottleneck_synthesis"
        ),
    }


def _missing_route(name: str, route_type: str, reason: str) -> dict[str, Any]:
    return {
        "name": name,
        "route_type": route_type,
        "status": "inconclusive",
        "mathematically_admissible": None,
        "runtime_effect": None,
        "reasons": [reason],
        "next_gate": "provide_missing_source_artifact",
    }


def _spatial_summary(report: dict[str, Any]) -> dict[str, Any]:
    screens = report.get("screens") or []
    means = []
    mode_means = []
    low_flags = []
    for screen in screens:
        summary = ((screen.get("group_summaries") or {}).get("all") or {})
        endpoint = ((summary.get("endpoint_pairwise_mean_m") or {}).get("mean"))
        mode = ((summary.get("mode_count") or {}).get("mean"))
        if endpoint is not None:
            means.append(float(endpoint))
        if mode is not None:
            mode_means.append(float(mode))
        evidence = screen.get("spatial_bottleneck_evidence") or {}
        low_flags.append(bool(evidence.get("global_low_diversity_evidence")))
    return {
        "records": report.get("records") or {},
        "screen_count": len(screens),
        "max_endpoint_pairwise_mean_m": max(means) if means else 0.0,
        "max_mode_count_mean": max(mode_means) if mode_means else 0.0,
        "all_screens_low_mode": bool(low_flags) and all(low_flags),
    }


def _decision(routes: list[dict[str, Any]]) -> dict[str, Any]:
    conditional = [route["name"] for route in routes if route["status"] == "conditional_next_design"]
    rejected = [route["name"] for route in routes if route["status"] == "rejected"]
    if conditional:
        status = "next_design_preflight_has_conditional_paths"
        reasons = ["conditional_paths_require_math_definition_before_replay"]
        next_step = (
            "Choose one conditional path and write a predeclared math/design "
            "gate. Do not run replay, Full36, formal seeds, or CAMP retraining "
            "until that gate proves no-leak current-tick compatibility."
        )
    elif rejected:
        status = "next_design_preflight_all_known_paths_rejected"
        reasons = ["no_conditional_path_from_available_artifacts"]
        next_step = (
            "Reject this design cycle and gather a materially new artifact or "
            "mathematical idea before further implementation."
        )
    else:
        status = "next_design_preflight_inconclusive"
        reasons = ["missing_or_inconclusive_source_artifacts"]
        next_step = "Provide missing artifacts or rerun source diagnostics."
    return {
        "status": status,
        "reasons": reasons,
        "conditional_paths": conditional,
        "rejected_paths": rejected,
        "online_selector_authorized": False,
        "closed_loop_smoke_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "camp_retraining_authorized": False,
        "next_step": next_step,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# DP CAMP Next Design Gate Preflight",
        "",
        "This is a read-only design preflight. It does not run DP, train CAMP, change online selection, run Full36, or use formal seeds.",
        "",
        "## Verdict",
        "",
        f"- Status: `{decision['status']}`",
        f"- Conditional paths: `{', '.join(decision['conditional_paths']) or 'none'}`",
        f"- Rejected paths: `{', '.join(decision['rejected_paths']) or 'none'}`",
        f"- Online selector authorized: `{decision['online_selector_authorized']}`",
        f"- CAMP retraining authorized: `{decision['camp_retraining_authorized']}`",
        "",
        "Reasons:",
    ]
    for reason in decision["reasons"]:
        lines.append(f"- `{reason}`")
    lines.extend(
        [
            "",
            "## Design Routes",
            "",
            "| Route | Type | Status | Next gate |",
            "| --- | --- | --- | --- |",
        ]
    )
    for route in report["design_routes"]:
        lines.append(
            f"| `{route['name']}` | `{route['route_type']}` | "
            f"`{route['status']}` | `{route['next_gate']}` |"
        )
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            f"Next step: {decision['next_step']}",
            "",
        ]
    )
    return "\n".join(lines)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def _load_named_reports(values: list[str]) -> dict[str, dict[str, Any]]:
    reports: dict[str, dict[str, Any]] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--spatial_diversity_json entries must be NAME=PATH.")
        name, path_text = value.split("=", 1)
        if not name:
            raise ValueError("--spatial_diversity_json name must not be empty.")
        reports[name] = _load_json(Path(path_text))
    return reports


def _path_or_none(path: Path | None) -> str | None:
    return None if path is None else str(path)


def _decision_status(report: dict[str, Any]) -> str | None:
    decision = report.get("final_decision") or {}
    status = decision.get("status")
    return str(status) if status is not None else None


def _get(data: dict[str, Any], *path: str) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


if __name__ == "__main__":
    main()
