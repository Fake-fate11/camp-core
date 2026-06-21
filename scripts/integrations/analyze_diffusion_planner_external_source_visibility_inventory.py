#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SOURCE_STATUS = "scenario_objective_redesign_boundary_and_external_source_contract_ready"
SOURCE_NEXT_WORK = "external_source_visibility_inventory_or_pause_only"

READY_STATUS = "external_source_visibility_inventory_has_design_candidate"
REJECT_STATUS = "external_source_visibility_inventory_no_deployable_source"
BLOCKED_STATUS = "external_source_visibility_inventory_source_not_ready"

AUTHORIZED_NEXT_WORK = "predeclare_default_off_external_context_payload_design_only"

BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "closed_loop_replay_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)

REQUIRED_CONTRACT_PROPERTIES = frozenset(
    {
        "current_tick_available_before_selection",
        "candidate_level_or_candidate_context_joinable",
        "finite_and_deterministic_for_fixed_tick",
        "not_a_closed_score_family_or_proxy",
        "not_future_outcome_label",
        "does_not_require_dp_modification_or_retraining",
        "latency_measurable_default_off",
        "atomizable_as_nonnegative_or_signed_split_coefficient",
        "preserves_affine_score_and_convex_master",
    }
)

TRAINING_OR_RESEARCH_PATH_MARKERS = (
    "/train_",
    "/valid_",
    "/rlvr/",
    "/exploration_policy/",
    "/preference_optimization/",
    "/util_scripts/",
    "/tests/",
    "/test_",
    "/docs/",
)

RUNTIME_PATH_MARKERS = (
    "/scenario_generation/",
    "/diffusion_planner_ros/",
    "/diffusion_planner/diffusion_planner/model/",
    "/diffusion_planner/diffusion_planner/dimensions.py",
)


@dataclass(frozen=True)
class ExternalSourceSpec:
    name: str
    hypothesis_family: str
    token_groups: tuple[tuple[str, ...], ...]
    boundary_tokens: tuple[str, ...]
    candidate_level: bool
    candidate_context_joinable: bool
    closed_score_family: str | None
    requires_dp_modification: bool
    atomization_sketch: str
    no_leak_argument: str
    latency_plan: str
    next_gate: str | None


EXTERNAL_SOURCE_SPECS: tuple[ExternalSourceSpec, ...] = (
    ExternalSourceSpec(
        name="traffic_signal_phase_timing_or_right_of_way_state",
        hypothesis_family="traffic_signal_phase_timing_or_right_of_way",
        token_groups=(
            ("TrafficLightController", "_GroupState", "duration", "last_change_time"),
            ("color_for_lanelet", "t_sec"),
            ("scene.map_data.lanes[:, :, 8:13]", "sim_time_s"),
        ),
        boundary_tokens=("TrafficLightController", "tick", "sim_time_s"),
        candidate_level=False,
        candidate_context_joinable=True,
        closed_score_family=None,
        requires_dp_modification=False,
        atomization_sketch=(
            "For each fixed candidate, compute nonnegative time/distance-to-signal "
            "or right-of-way margins from current controller state and signed-split "
            "any directional residuals before adding them as coefficients a_k."
        ),
        no_leak_argument=(
            "Uses only simulator traffic-light state available at the current tick "
            "before selection; future closed-loop outcomes remain labels only."
        ),
        latency_plan=(
            "Default-off payload must time only controller-state lookup and "
            "candidate-context joining, separate from DP generation."
        ),
        next_gate=AUTHORIZED_NEXT_WORK,
    ),
    ExternalSourceSpec(
        name="route_speed_limit_and_control_context",
        hypothesis_family="map_or_route_control_context_not_already_closed",
        token_groups=(
            ("route_lanes_speed_limit", "route_lanes_has_speed_limit"),
            ("lanes_speed_limit", "lanes_has_speed_limit"),
            ("speed_limit_emb", "route_speed_limit"),
        ),
        boundary_tokens=("route_lanes_speed_limit", "to_model_tensors"),
        candidate_level=False,
        candidate_context_joinable=True,
        closed_score_family=None,
        requires_dp_modification=False,
        atomization_sketch=(
            "Join each fixed candidate with current route speed/control context; "
            "encode nonnegative speed-limit exceedance, missing-limit masks, or "
            "signed-split control residuals as coefficients a_k."
        ),
        no_leak_argument=(
            "Speed-limit and route-control tensors are current map/context inputs, "
            "not simulator outcome labels."
        ),
        latency_plan=(
            "Default-off payload must report route/control context extraction "
            "latency and candidate join latency separately."
        ),
        next_gate=AUTHORIZED_NEXT_WORK,
    ),
    ExternalSourceSpec(
        name="dp_native_log_probability_or_candidate_score",
        hypothesis_family="dp_native_candidate_prior_or_uncertainty",
        token_groups=(
            ("log_prob",),
            ("logprob",),
            ("candidate_score",),
        ),
        boundary_tokens=("prediction", "turn_indicator_logit"),
        candidate_level=True,
        candidate_context_joinable=False,
        closed_score_family=None,
        requires_dp_modification=True,
        atomization_sketch=(
            "Would require a per-candidate DP prior coefficient, but this is not "
            "admissible unless already exposed at the wrapper boundary."
        ),
        no_leak_argument=(
            "A native prior would be no-leak only if emitted before selection and "
            "not derived from closed-loop reward."
        ),
        latency_plan="Not latency-actionable until the boundary exposure exists.",
        next_gate=None,
    ),
    ExternalSourceSpec(
        name="denoising_residual_or_uncertainty",
        hypothesis_family="dp_native_candidate_prior_or_uncertainty",
        token_groups=(
            ("sampled_trajectories", "model_output"),
            ("denois", "residual"),
            ("variance", "uncertainty"),
        ),
        boundary_tokens=("return", "prediction", "turn_indicator_logit"),
        candidate_level=True,
        candidate_context_joinable=False,
        closed_score_family=None,
        requires_dp_modification=True,
        atomization_sketch=(
            "Would need a per-candidate uncertainty/residual coefficient. It is "
            "not admissible if only present as an internal decoder tensor."
        ),
        no_leak_argument=(
            "Internal diffusion state would be current-tick, but only if exposed "
            "without modifying DP and without using rewards."
        ),
        latency_plan="Not latency-actionable until the boundary exposure exists.",
        next_gate=None,
    ),
    ExternalSourceSpec(
        name="turn_indicator_logits",
        hypothesis_family="dp_native_candidate_prior_or_uncertainty",
        token_groups=(
            ("turn_indicator_logit",),
            ("turn_logits",),
        ),
        boundary_tokens=("turn_indicator_logit",),
        candidate_level=True,
        candidate_context_joinable=False,
        closed_score_family="turn_logit_atom_family",
        requires_dp_modification=False,
        atomization_sketch=(
            "Already handled by the closed turn-logit family; do not reopen it "
            "as a new atom source."
        ),
        no_leak_argument="Current-tick, but already closed by prior evidence.",
        latency_plan="No new latency plan; route remains closed.",
        next_gate=None,
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only DP external-source visibility inventory. This consumes "
            "the latest scenario/objective external-source contract and scans "
            "source text for current-tick candidate/context sources. It does "
            "not run DP, train CAMP, replay, or change selection."
        )
    )
    parser.add_argument("--source_contract_json", type=Path, required=True)
    parser.add_argument("--source_file", type=Path, action="append", default=[])
    parser.add_argument("--source_root", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        source_contract=_load_json(args.source_contract_json),
        source_files=args.source_file,
        source_roots=args.source_root,
        label=args.label,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def analyze(
    *,
    source_contract: dict[str, Any],
    source_files: list[Path],
    source_roots: list[Path],
    label: str | None = None,
) -> dict[str, Any]:
    source_gate = _source_gate(source_contract)
    files = _discover_source_files(source_files, source_roots)
    texts = _read_sources(files)
    rows = [_source_row(spec, texts) for spec in EXTERNAL_SOURCE_SPECS]
    design_candidates = [
        row
        for row in rows
        if row["admissibility_status"] == "design_candidate_requires_payload_gate"
    ]
    rejected_visible = [
        row for row in rows if row["visible"] and row not in design_candidates
    ]
    final = _decision(source_gate=source_gate, design_candidates=design_candidates)
    return {
        "analysis": {
            "name": "dp_camp_external_source_visibility_inventory_v1",
            "label": label,
            "role": (
                "read-only external-source visibility inventory after the "
                "scenario/objective boundary contract"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_leakage": False,
            "math_boundary": (
                "This inventory scans source text only. It creates no atom, "
                "runs no replay, trains no weights, and modifies neither DP nor "
                "the selector. A future payload must expose fixed current-tick "
                "finite-candidate coefficients a_k, nonnegative or signed-split, "
                "so score_k(w)=a_k^T w remains affine and the simplex/CVaR/L2 "
                "master remains convex. This is not a classical Benders "
                "decomposition."
            ),
        },
        "source_gate": source_gate,
        "inputs": {
            "source_files": [str(path) for path in source_files],
            "source_roots": [str(path) for path in source_roots],
            "discovered_files": [str(path) for path in files],
        },
        "source_rows": rows,
        "design_candidates": design_candidates,
        "rejected_visible_sources": rejected_visible,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": final,
    }


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    final = report.get("final_decision") or {}
    contract = report.get("external_source_visibility_contract") or {}
    required = set(contract.get("required_properties") or [])
    missing = sorted(REQUIRED_CONTRACT_PROPERTIES - required)
    conflicts = [key for key in BLOCKED_ACTIONS if bool(final.get(key))]
    return {
        "status": final.get("status"),
        "passed": (
            bool(final.get("passed"))
            and final.get("status") == SOURCE_STATUS
            and final.get("authorized_next_work") == SOURCE_NEXT_WORK
            and bool(final.get("external_source_contract_ready"))
            and not missing
            and not conflicts
        ),
        "authorized_next_work": final.get("authorized_next_work"),
        "external_source_contract_ready": final.get("external_source_contract_ready"),
        "required_properties": sorted(required),
        "missing_required_properties": missing,
        "blocked_action_conflicts": conflicts,
    }


def _discover_source_files(source_files: list[Path], source_roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in source_files:
        if path.is_file():
            files.append(path)
    for root in source_roots:
        if root.is_file():
            files.append(root)
        elif root.is_dir():
            files.extend(
                sorted(
                    path
                    for path in root.rglob("*")
                    if path.is_file()
                    and path.suffix.lower() in {".py", ".md", ".yaml", ".yml", ".json"}
                )
            )
    return sorted(dict.fromkeys(files))


def _read_sources(files: list[Path]) -> dict[str, str]:
    texts: dict[str, str] = {}
    for path in files:
        try:
            texts[str(path)] = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
    return texts


def _source_row(spec: ExternalSourceSpec, texts: dict[str, str]) -> dict[str, Any]:
    group_hits = []
    for tokens in spec.token_groups:
        hit_files = [
            _normalize_path(path)
            for path, text in texts.items()
            if all(token in text for token in tokens)
        ]
        group_hits.append({"tokens": list(tokens), "files": hit_files})
    visible_files = sorted({path for group in group_hits for path in group["files"]})
    runtime_files = [path for path in visible_files if _path_scope(path) == "runtime"]
    non_runtime_files = [path for path in visible_files if _path_scope(path) != "runtime"]
    boundary_files = [
        _normalize_path(path)
        for path, text in texts.items()
        if _normalize_path(path) in runtime_files
        and all(token in text for token in spec.boundary_tokens)
    ]
    visible = bool(visible_files)
    runtime_visible = bool(runtime_files)
    boundary_visible = bool(boundary_files)
    closed = spec.closed_score_family is not None
    context_joinable = bool(spec.candidate_level or spec.candidate_context_joinable)
    if not visible:
        status = "not_visible"
    elif not runtime_visible:
        status = "visible_only_in_training_or_research_paths"
    elif closed:
        status = "visible_but_closed_score_family"
    elif spec.requires_dp_modification:
        status = "visible_but_requires_dp_modification_or_internal_tensor_exposure"
    elif not context_joinable:
        status = "visible_but_not_candidate_joinable"
    elif not boundary_visible:
        status = "visible_but_boundary_exposure_not_proven"
    else:
        status = "design_candidate_requires_payload_gate"
    return {
        **asdict(spec),
        "visible": visible,
        "runtime_visible": runtime_visible,
        "boundary_visible": boundary_visible,
        "context_joinable": context_joinable,
        "closed_by_score_inventory": closed,
        "admissibility_status": status,
        "group_hits": group_hits,
        "visible_files": visible_files,
        "runtime_visible_files": runtime_files,
        "non_runtime_visible_files": non_runtime_files,
        "boundary_visible_files": boundary_files,
    }


def _path_scope(path: str) -> str:
    normalized = "/" + path.replace("\\", "/").lstrip("./")
    marker = "/Diffusion-Planner/"
    if marker in normalized:
        normalized = "/" + normalized.split(marker, 1)[1]
    if any(marker in normalized for marker in TRAINING_OR_RESEARCH_PATH_MARKERS):
        return "training_or_research"
    if any(marker in normalized for marker in RUNTIME_PATH_MARKERS):
        return "runtime"
    return "other"


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/")


def _decision(
    *,
    source_gate: dict[str, Any],
    design_candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    if not source_gate["passed"]:
        return {
            "status": BLOCKED_STATUS,
            "passed": False,
            "primary_gap": "source_contract_not_ready",
            "design_candidate_names": [],
            "authorized_next_work": "fix_external_source_contract_before_inventory",
            "next_step": (
                "Regenerate or fix the scenario/objective external-source "
                "contract before scanning source visibility."
            ),
            **{key: False for key in BLOCKED_ACTIONS},
        }
    if design_candidates:
        return {
            "status": READY_STATUS,
            "passed": True,
            "primary_gap": "current_tick_context_source_visible_but_payload_gate_required",
            "design_candidate_names": [row["name"] for row in design_candidates],
            "authorized_next_work": AUTHORIZED_NEXT_WORK,
            "next_step": (
                "Predeclare a default-off payload design for the visible "
                "current-tick context sources. Do not train, replay, or promote "
                "a selector until that design gate passes."
            ),
            **{key: False for key in BLOCKED_ACTIONS},
        }
    return {
        "status": REJECT_STATUS,
        "passed": True,
        "primary_gap": "no_new_visible_current_tick_candidate_or_context_source",
        "design_candidate_names": [],
        "authorized_next_work": (
            "reject_external_source_visibility_route_or_redefine_scenario_objective"
        ),
        "next_step": (
            "Reject this external-source route unless a new source is supplied. "
            "Do not train, replay, or promote a selector."
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# DP-CAMP External Source Visibility Inventory",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Primary gap: `{decision['primary_gap']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Source Rows",
        "",
        "| Source | Family | Visible | Runtime | Boundary | Status | Closed | Next Gate |",
        "| --- | --- | ---: | ---: | ---: | --- | ---: | --- |",
    ]
    for row in report["source_rows"]:
        lines.append(
            f"| `{row['name']}` | `{row['hypothesis_family']}` | "
            f"`{row['visible']}` | `{row['runtime_visible']}` | "
            f"`{row['boundary_visible']}` | `{row['admissibility_status']}` | "
            f"`{row['closed_by_score_inventory']}` | `{row['next_gate'] or 'none'}` |"
        )
    lines.extend(
        [
            "",
            "## Design Candidates",
            "",
        ]
    )
    if report["design_candidates"]:
        for row in report["design_candidates"]:
            lines.extend(
                [
                    f"### `{row['name']}`",
                    "",
                    f"- Atomization sketch: {row['atomization_sketch']}",
                    f"- No-leak argument: {row['no_leak_argument']}",
                    f"- Latency plan: {row['latency_plan']}",
                    "- Boundary files: "
                    + ", ".join(f"`{path}`" for path in row["boundary_visible_files"]),
                    "",
                ]
            )
    else:
        lines.append("No design candidate passed the visibility inventory.")
        lines.append("")
    lines.extend(
        [
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
