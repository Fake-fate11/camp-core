#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]

VISIBILITY_REQUIRED_STATUS = "current_tick_tensor_visibility_has_candidate_source"
VISIBILITY_REQUIRED_SOURCE = "turn_indicator_logits"
VISIBILITY_REQUIRED_NEXT_WORK = "predeclare_default_off_turn_logit_candidate_payload_design_only"

READY_STATUS = "turn_logit_payload_design_ready"
REJECT_STATUS = "turn_logit_payload_design_rejected"
SOURCE_BLOCKED_STATUS = "turn_logit_payload_design_source_not_ready"

NEXT_WORK = "default_off_turn_logit_payload_implementation_unit_tests_only"

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
class PayloadFieldSpec:
    name: str
    shape: str
    dtype: str
    source: str
    null_behavior: str
    finite_check: str
    latency_bucket: str
    candidate_level: bool = True
    default_off: bool = True
    selection_effect: bool = False
    uses_future_outcomes: bool = False
    requires_dp_modification: bool = False


@dataclass(frozen=True)
class AtomCandidateSpec:
    name: str
    source_fields: tuple[str, ...]
    formula: str
    nonnegative_argument: str
    convexity_note: str
    candidate_level: bool = True
    uses_future_outcomes: bool = False


@dataclass(frozen=True)
class SourceHook:
    name: str
    file_role: str
    required_tokens: tuple[str, ...]
    rationale: str


PAYLOAD_FIELDS: tuple[PayloadFieldSpec, ...] = (
    PayloadFieldSpec(
        name="candidate_turn_indicator_logits",
        shape="[K,C] or null",
        dtype="float32",
        source="turn_logits returned by generate_candidate_trajectories(...)",
        null_behavior=(
            "null when DP output lacks turn_indicator_logit; payload must record "
            "available=false and no atomization candidates may be considered"
        ),
        finite_check="if present, shape[0] == candidate_count and all values finite",
        latency_bucket="latency_ms_turn_logit_payload",
    ),
    PayloadFieldSpec(
        name="candidate_turn_indicator_probabilities",
        shape="[K,C] or null",
        dtype="float32",
        source="softmax(candidate_turn_indicator_logits, axis=-1)",
        null_behavior="null whenever logits are null",
        finite_check="if present, finite values in [0,1] and row sums within tolerance",
        latency_bucket="latency_ms_turn_logit_payload",
    ),
    PayloadFieldSpec(
        name="candidate_turn_indicator_top_class",
        shape="[K] or null",
        dtype="int32",
        source="argmax(candidate_turn_indicator_probabilities, axis=-1)",
        null_behavior="null whenever logits are null",
        finite_check="if present, integer class id in [0,C)",
        latency_bucket="latency_ms_turn_logit_payload",
    ),
)


ATOM_CANDIDATES: tuple[AtomCandidateSpec, ...] = (
    AtomCandidateSpec(
        name="turn_logit_entropy_cost_v1",
        source_fields=("candidate_turn_indicator_probabilities",),
        formula="-sum_c p_kc log(max(p_kc, eps)) / log(C)",
        nonnegative_argument="normalized categorical entropy is in [0,1] for C >= 2",
        convexity_note=(
            "entropy is computed after DP inference as a fixed candidate "
            "coefficient; no trajectory-coordinate convexity claim is made"
        ),
    ),
    AtomCandidateSpec(
        name="turn_logit_margin_shortfall_v1",
        source_fields=("candidate_turn_indicator_probabilities",),
        formula="max(0, margin_budget - (top1_prob_k - top2_prob_k))",
        nonnegative_argument="outer hinge clamps the margin shortfall at zero",
        convexity_note="fixed coefficient a_k keeps score_k(w)=a_k^T w affine",
    ),
    AtomCandidateSpec(
        name="turn_logit_non_top1_disagreement_v1",
        source_fields=("candidate_turn_indicator_top_class",),
        formula="1[top_class_k != top_class_0]",
        nonnegative_argument="indicator is either 0 or 1",
        convexity_note=(
            "candidate0-relative disagreement is fixed at the current tick and "
            "does not change the convexity of the robust master in w"
        ),
    ),
)


SOURCE_HOOKS: tuple[SourceHook, ...] = (
    SourceHook(
        name="candidate_generation_returns_turn_logits",
        file_role="replay",
        required_tokens=(
            "candidates, neighbor_predictions, turn_logits = generate_candidate_trajectories",
            "turn_logits",
        ),
        rationale="the wrapper must already receive all candidate logits before selection",
    ),
    SourceHook(
        name="generator_extracts_optional_turn_logits",
        file_role="integration",
        required_tokens=(
            "outputs.get(\"turn_indicator_logit\")",
            "return ego_candidates, predictions[:, 1:], turn_logits",
        ),
        rationale="turn logits must be optional DP model outputs, not DP code changes",
    ),
    SourceHook(
        name="selected_turn_indicator_behavior_is_separate",
        file_role="replay",
        required_tokens=(
            "chosen_logits = turn_logits[selected_index].copy()",
            "turn_indicators[ego_id]",
        ),
        rationale=(
            "existing simulator turn-indicator behavior uses only the selected "
            "candidate and must remain unchanged by default-off logging"
        ),
    ),
    SourceHook(
        name="selection_log_append_available",
        file_role="replay",
        required_tokens=("records.append", "latency_ms_including_candidate_generation"),
        rationale="default-off payload can be recorded at the existing selection-log site",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only preflight for default-off turn-logit candidate payload "
            "logging. It consumes the current-tick tensor visibility artifact "
            "and source files, but does not run replay, train CAMP, or change "
            "selection."
        )
    )
    parser.add_argument("--tensor_visibility_json", type=Path, required=True)
    parser.add_argument(
        "--replay_source",
        type=Path,
        default=ROOT / "scripts/integrations/run_diffusion_planner_camp_replay.py",
    )
    parser.add_argument(
        "--integration_source",
        type=Path,
        default=ROOT / "camp_core/camp_core/integrations/diffusion_planner.py",
    )
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        visibility_report=_load_json(args.tensor_visibility_json),
        replay_source=args.replay_source,
        integration_source=args.integration_source,
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
    visibility_report: dict[str, Any],
    replay_source: Path,
    integration_source: Path,
    label: str | None = None,
    payload_fields: tuple[PayloadFieldSpec, ...] = PAYLOAD_FIELDS,
    atom_candidates: tuple[AtomCandidateSpec, ...] = ATOM_CANDIDATES,
    source_hooks: tuple[SourceHook, ...] = SOURCE_HOOKS,
) -> dict[str, Any]:
    visibility = _visibility_gate(visibility_report)
    replay_text = _read_source(replay_source)
    integration_text = _read_source(integration_source)
    hook_reports = [
        _hook_report(hook, replay_text, integration_text) for hook in source_hooks
    ]
    payload_reports = [_payload_field_report(field) for field in payload_fields]
    atom_reports = [_atom_candidate_report(atom) for atom in atom_candidates]
    design_checks = _design_checks(payload_reports, atom_reports, hook_reports)
    final = _decision(visibility=visibility, checks=design_checks)
    return {
        "analysis": {
            "name": "dp_camp_turn_logit_payload_design_v1",
            "label": label,
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "default_off_logging_only": True,
            "future_outcome_leakage": False,
            "replay_source": str(replay_source),
            "integration_source": str(integration_source),
            "accept_criteria": {
                "visibility_status": VISIBILITY_REQUIRED_STATUS,
                "visibility_candidate_source": VISIBILITY_REQUIRED_SOURCE,
                "visibility_authorized_next_work": VISIBILITY_REQUIRED_NEXT_WORK,
                "all_required_source_hooks_found": True,
                "all_payload_fields_default_off": True,
                "all_payload_fields_no_outcome_leakage": True,
                "all_payload_fields_no_selection_effect": True,
                "all_payload_fields_no_dp_modification": True,
                "all_atom_candidates_nonnegative_fixed_coefficients": True,
            },
            "math_boundary": (
                "DP remains a frozen black-box candidate generator. The proposed "
                "payload only records optional per-candidate turn logits that "
                "are already returned before selection. The payload is "
                "default-off, null-safe, and selection-neutral. If later "
                "atomized, entropy, margin-shortfall, and candidate0-relative "
                "turn-disagreement values are fixed current-tick candidate "
                "coefficients a_k, so CAMP score_k(w)=a_k^T w remains affine "
                "and the simplex/CVaR/L2 robust master remains convex in w. "
                "No DP-side classical Benders decomposition, dual, or cut is "
                "constructed or claimed."
            ),
        },
        "source_tensor_visibility_gate": visibility,
        "payload_fields": payload_reports,
        "atomization_candidates": atom_reports,
        "source_hook_reports": hook_reports,
        "design_checks": design_checks,
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": final,
    }


def _visibility_gate(report: dict[str, Any]) -> dict[str, Any]:
    decision = report.get("final_decision") or {}
    status = str(decision.get("status") or "")
    candidate_sources = [str(item) for item in decision.get("candidate_source_names") or []]
    authorized_next_work = decision.get("authorized_next_work")
    return {
        "status": status,
        "candidate_source_names": candidate_sources,
        "authorized_next_work": authorized_next_work,
        "passed": (
            status == VISIBILITY_REQUIRED_STATUS
            and candidate_sources == [VISIBILITY_REQUIRED_SOURCE]
            and authorized_next_work == VISIBILITY_REQUIRED_NEXT_WORK
        ),
    }


def _payload_field_report(field: PayloadFieldSpec) -> dict[str, Any]:
    payload = asdict(field)
    payload["valid_for_design"] = (
        field.candidate_level
        and field.default_off
        and not field.selection_effect
        and not field.uses_future_outcomes
        and not field.requires_dp_modification
    )
    return payload


def _atom_candidate_report(atom: AtomCandidateSpec) -> dict[str, Any]:
    payload = asdict(atom)
    payload["valid_for_design"] = (
        atom.candidate_level and not atom.uses_future_outcomes
    )
    return payload


def _hook_report(
    hook: SourceHook,
    replay_text: str,
    integration_text: str,
) -> dict[str, Any]:
    if hook.file_role == "replay":
        text = replay_text
    elif hook.file_role == "integration":
        text = integration_text
    else:
        raise ValueError(f"Unknown source hook file_role: {hook.file_role}")
    missing = [token for token in hook.required_tokens if token not in text]
    return {
        "name": hook.name,
        "file_role": hook.file_role,
        "required_tokens": list(hook.required_tokens),
        "rationale": hook.rationale,
        "found": not missing,
        "missing_tokens": missing,
    }


def _design_checks(
    payload_reports: list[dict[str, Any]],
    atom_reports: list[dict[str, Any]],
    hook_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    invalid_payload_fields = [
        str(field["name"])
        for field in payload_reports
        if not bool(field["valid_for_design"])
    ]
    invalid_atom_candidates = [
        str(atom["name"]) for atom in atom_reports if not bool(atom["valid_for_design"])
    ]
    missing_hooks = [
        str(hook["name"]) for hook in hook_reports if not bool(hook["found"])
    ]
    return {
        "invalid_payload_fields": invalid_payload_fields,
        "invalid_atom_candidates": invalid_atom_candidates,
        "missing_source_hooks": missing_hooks,
        "all_payload_fields_default_off": all(
            bool(field["default_off"]) for field in payload_reports
        ),
        "all_payload_fields_no_outcome_leakage": all(
            not bool(field["uses_future_outcomes"]) for field in payload_reports
        ),
        "all_payload_fields_no_selection_effect": all(
            not bool(field["selection_effect"]) for field in payload_reports
        ),
        "all_payload_fields_no_dp_modification": all(
            not bool(field["requires_dp_modification"]) for field in payload_reports
        ),
        "atom_candidate_count": len(atom_reports),
        "passed": (
            not invalid_payload_fields
            and not invalid_atom_candidates
            and not missing_hooks
            and len(atom_reports) >= 3
        ),
    }


def _decision(
    *,
    visibility: dict[str, Any],
    checks: dict[str, Any],
) -> dict[str, Any]:
    if not visibility["passed"]:
        status = SOURCE_BLOCKED_STATUS
        primary_gap = "tensor_visibility_source_not_turn_logits_only"
        authorized_next_work = None
        next_step = (
            "Run this design only after tensor visibility identifies exactly "
            "turn_indicator_logits as the next source."
        )
    elif checks["passed"]:
        status = READY_STATUS
        primary_gap = "default_off_turn_logit_payload_design_ready"
        authorized_next_work = NEXT_WORK
        next_step = (
            "Implement only the default-off turn-logit payload with unit tests. "
            "Replay, selector changes, formal seeds, and CAMP retraining remain "
            "blocked until that implementation gate passes."
        )
    else:
        status = REJECT_STATUS
        primary_gap = "turn_logit_payload_design_incomplete"
        authorized_next_work = None
        next_step = (
            "Fix source hooks, payload field contracts, or atomization candidates "
            "before implementation."
        )
    return {
        "status": status,
        "passed": status == READY_STATUS,
        "primary_gap": primary_gap,
        "authorized_next_work": authorized_next_work,
        **{key: False for key in BLOCKED_ACTIONS},
        "next_step": next_step,
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# Turn-Logit Payload Design",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Primary gap: `{decision['primary_gap']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Payload Fields",
        "",
        "| Field | Shape | Null Behavior |",
        "| --- | --- | --- |",
    ]
    for field in report["payload_fields"]:
        lines.append(
            f"| `{field['name']}` | `{field['shape']}` | "
            f"{field['null_behavior']} |"
        )
    lines.extend(
        [
            "",
            "## Atomization Candidates",
            "",
            "| Atom | Formula | Nonnegative Argument |",
            "| --- | --- | --- |",
        ]
    )
    for atom in report["atomization_candidates"]:
        lines.append(
            f"| `{atom['name']}` | `{atom['formula']}` | "
            f"{atom['nonnegative_argument']} |"
        )
    lines.extend(
        [
            "",
            "## Source Hooks",
            "",
            "| Hook | Found | Missing Tokens |",
            "| --- | ---: | --- |",
        ]
    )
    for hook in report["source_hook_reports"]:
        missing = ", ".join(f"`{token}`" for token in hook["missing_tokens"])
        lines.append(
            f"| `{hook['name']}` | `{hook['found']}` | {missing or '`none`'} |"
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


def _read_source(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
