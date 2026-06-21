#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SOURCE_REQUIRED_STATUS = "post_closure_state_remainder_requires_source_visibility_inventory"
READY_STATUS = "current_tick_tensor_visibility_has_candidate_source"
REJECT_STATUS = "current_tick_tensor_visibility_no_new_candidate_source"
SOURCE_BLOCKED_STATUS = "current_tick_tensor_visibility_source_not_ready"

REQUIRED_CLOSED_SCORE_FAMILIES = frozenset(
    {
        "non_turn_interaction_family",
        "observable_interaction_family",
        "progress_lane_hard_context",
        "relaxed_strict_atom_family",
        "revised_context_atom_family",
    }
)

BLOCKED_ACTIONS = (
    "new_replay_authorized",
    "closed_loop_smoke_authorized",
    "online_selector_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "camp_retraining_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


@dataclass(frozen=True)
class TensorSourceSpec:
    name: str
    required_tokens: tuple[str, ...]
    source_kind: str
    candidate_level: bool
    runtime_admissible: bool
    rationale: str
    next_gate: str | None


TENSOR_SOURCES: tuple[TensorSourceSpec, ...] = (
    TensorSourceSpec(
        name="turn_indicator_logits",
        required_tokens=("turn_indicator_logit", "turn_logits"),
        source_kind="optional_dp_model_output",
        candidate_level=True,
        runtime_admissible=True,
        rationale=(
            "generate_candidate_trajectories already extracts optional "
            "per-candidate turn_indicator_logit values before selection; the "
            "wrapper currently uses only the selected candidate when the "
            "simulator asks for turn indicators"
        ),
        next_gate="predeclare_default_off_turn_logit_candidate_payload_design_only",
    ),
    TensorSourceSpec(
        name="dp_native_log_probability_or_score",
        required_tokens=("log_prob", "candidate_score"),
        source_kind="dp_internal_score",
        candidate_level=True,
        runtime_admissible=True,
        rationale=(
            "would be a direct DP prior over candidates if exposed before "
            "selection, but it must be visible without DP modification"
        ),
        next_gate="predeclare_default_off_dp_prior_score_payload_design_only",
    ),
    TensorSourceSpec(
        name="denoising_residual_or_intermediate",
        required_tokens=("denois", "residual"),
        source_kind="dp_internal_diffusion_state",
        candidate_level=True,
        runtime_admissible=True,
        rationale=(
            "could describe candidate uncertainty or model correction effort, "
            "but only if exposed at the wrapper boundary without modifying DP"
        ),
        next_gate="predeclare_default_off_denoising_residual_payload_design_only",
    ),
    TensorSourceSpec(
        name="wrapper_sampled_latent_noise",
        required_tokens=("sampled_trajectories", "torch.randn", "latent"),
        source_kind="wrapper_candidate_generation_control",
        candidate_level=True,
        runtime_admissible=False,
        rationale=(
            "this is the wrapper-created random candidate seed, not a DP "
            "preference or safety signal; simple candidate-generation/noise "
            "routes were already rejected"
        ),
        next_gate=None,
    ),
    TensorSourceSpec(
        name="neighbor_prediction_tensor",
        required_tokens=("neighbor_predictions", "_candidate_obstacles"),
        source_kind="already_logged_interaction_geometry",
        candidate_level=True,
        runtime_admissible=False,
        rationale=(
            "neighbor predictions are already consumed through clearance and "
            "observable interaction families that the post-closure inventory "
            "closed"
        ),
        next_gate=None,
    ),
    TensorSourceSpec(
        name="guidance_energy_or_scale",
        required_tokens=("_guidance_fn", "_guidance_scale"),
        source_kind="candidate_generation_control",
        candidate_level=False,
        runtime_admissible=False,
        rationale=(
            "guidance controls alter candidate generation rather than providing "
            "a fixed candidate-level score feature; generator-control routes "
            "must not be revived here"
        ),
        next_gate=None,
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only source/tensor visibility inventory after logged "
            "observable-state score families have closed. This scans source "
            "files for current-tick candidate tensors but does not run DP, "
            "train CAMP, or change selection."
        )
    )
    parser.add_argument("--post_closure_remainder_json", type=Path, required=True)
    parser.add_argument("--source_file", type=Path, action="append", default=[])
    parser.add_argument("--source_root", type=Path, action="append", default=[])
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        post_closure_remainder=_load_json(args.post_closure_remainder_json),
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
    post_closure_remainder: dict[str, Any],
    source_files: list[Path],
    source_roots: list[Path],
    label: str | None = None,
) -> dict[str, Any]:
    source_gate = _source_gate(post_closure_remainder)
    files = _discover_source_files(source_files, source_roots)
    texts = _read_sources(files)
    tensor_sources = [_tensor_source_row(spec, texts) for spec in TENSOR_SOURCES]
    candidate_sources = [
        row
        for row in tensor_sources
        if row["visible"]
        and row["candidate_level"]
        and row["runtime_admissible"]
        and row["next_gate"]
    ]
    final = _decision(source_gate=source_gate, candidate_sources=candidate_sources)
    return {
        "analysis": {
            "name": "dp_camp_current_tick_tensor_visibility_v1",
            "label": label,
            "role": (
                "read-only source inventory for candidate-level current-tick "
                "tensors after logged observable-state score families closed"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "future_outcome_leakage": False,
            "math_boundary": (
                "This inventory scans source text only. It does not run the "
                "model, log new payloads, create atoms, train weights, use "
                "outcome labels, or construct a Benders master/subproblem. A "
                "future tensor payload would still need a separate default-off "
                "logging design gate and must enter CAMP only as fixed "
                "current-tick finite-candidate coefficients a_k so "
                "score_k(w)=a_k^T w remains affine."
            ),
        },
        "source_gate": source_gate,
        "inputs": {
            "source_files": [str(path) for path in source_files],
            "source_roots": [str(path) for path in source_roots],
            "discovered_python_files": [str(path) for path in files],
        },
        "tensor_sources": tensor_sources,
        "candidate_sources": candidate_sources,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": final,
    }


def _source_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    status = str(decision.get("status") or "")
    required_closed = set(report.get("required_closed_score_families") or [])
    missing_closed = set(decision.get("missing_closed_score_families") or [])
    missing_required = sorted(REQUIRED_CLOSED_SCORE_FAMILIES - required_closed)
    stale = bool(missing_closed or missing_required)
    return {
        "status": status,
        "passed": status == SOURCE_REQUIRED_STATUS and not stale,
        "required_status": SOURCE_REQUIRED_STATUS,
        "authorized_next_work": decision.get("authorized_next_work"),
        "missing_closed_score_families": sorted(missing_closed),
        "missing_required_closed_score_families": missing_required,
        "stale": stale,
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
            files.extend(sorted(root.rglob("*.py")))
    return sorted(dict.fromkeys(files))


def _read_sources(files: list[Path]) -> dict[str, str]:
    texts: dict[str, str] = {}
    for path in files:
        try:
            texts[str(path)] = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
    return texts


def _tensor_source_row(
    spec: TensorSourceSpec,
    texts: dict[str, str],
) -> dict[str, Any]:
    token_hits: dict[str, list[str]] = {}
    for token in spec.required_tokens:
        token_hits[token] = [
            path for path, text in texts.items() if token in text
        ]
    cooccurrence_files = [
        path
        for path, text in texts.items()
        if all(token in text for token in spec.required_tokens)
    ]
    visible = bool(cooccurrence_files)
    if visible and spec.runtime_admissible and spec.candidate_level:
        visibility_status = "candidate_tensor_source_visible"
    elif visible:
        visibility_status = "visible_but_not_runtime_admissible"
    else:
        visibility_status = "not_visible"
    return {
        **asdict(spec),
        "visible": visible,
        "visibility_status": visibility_status,
        "token_hits": token_hits,
        "cooccurrence_files": cooccurrence_files,
    }


def _decision(
    *,
    source_gate: dict[str, Any],
    candidate_sources: list[dict[str, Any]],
) -> dict[str, Any]:
    if not source_gate["passed"]:
        status = SOURCE_BLOCKED_STATUS
        if source_gate.get("stale"):
            primary_gap = "post_closure_remainder_missing_current_score_inventory_closure"
            authorized_next_work = "refresh_post_closure_remainder_before_tensor_inventory"
            next_step = (
                "Regenerate the post-closure remainder from the current "
                "score-family inventory before scanning tensor visibility."
            )
        else:
            primary_gap = "post_closure_remainder_source_not_ready"
            authorized_next_work = "fix_post_closure_remainder_before_tensor_inventory"
            next_step = "Run this inventory only after the post-closure remainder gate."
    elif candidate_sources:
        status = READY_STATUS
        primary_gap = "visible_runtime_admissible_candidate_tensor_source_found"
        authorized_next_work = candidate_sources[0]["next_gate"]
        next_step = (
            "Predeclare a default-off logging design for the visible candidate "
            "tensor source. Do not run replay until that design gate passes."
        )
    else:
        status = REJECT_STATUS
        primary_gap = "no_new_runtime_admissible_candidate_tensor_source_visible"
        authorized_next_work = "reject_tensor_visibility_route_or_redefine_scenario_objective"
        next_step = (
            "Do not add atoms from invisible or generator-control tensors. "
            "Return to scenario/objective redesign or a broader source audit."
        )
    return {
        "status": status,
        "passed": status == READY_STATUS,
        "primary_gap": primary_gap,
        "candidate_source_names": [row["name"] for row in candidate_sources],
        "authorized_next_work": authorized_next_work,
        **{key: False for key in BLOCKED_ACTIONS},
        "next_step": next_step,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# DP-CAMP Current-Tick Tensor Visibility Inventory",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Primary gap: `{decision['primary_gap']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Tensor Sources",
        "",
        "| Source | Visible | Status | Candidate Level | Runtime Admissible | Next Gate |",
        "| --- | ---: | --- | ---: | ---: | --- |",
    ]
    for row in report["tensor_sources"]:
        lines.append(
            f"| `{row['name']}` | `{row['visible']}` | "
            f"`{row['visibility_status']}` | `{row['candidate_level']}` | "
            f"`{row['runtime_admissible']}` | `{row['next_gate'] or 'none'}` |"
        )
    lines.extend(
        [
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This is not replay, not training, not selector promotion, and not "
            "a classical Benders decomposition.",
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
