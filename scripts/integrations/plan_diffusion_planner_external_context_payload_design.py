#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SOURCE_STATUS = "external_source_visibility_inventory_has_design_candidate"
SOURCE_NEXT_WORK = "predeclare_default_off_external_context_payload_design_only"

READY_STATUS = "external_context_payload_design_ready"
BLOCKED_STATUS = "external_context_payload_design_source_not_ready"
AUTHORIZED_NEXT_WORK = "default_off_external_context_payload_implementation_unit_tests_only"

REQUIRED_DESIGN_CANDIDATES = (
    "traffic_signal_phase_timing_or_right_of_way_state",
    "route_speed_limit_and_control_context",
)

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


@dataclass(frozen=True)
class PayloadFieldSpec:
    name: str
    family: str
    shape: str
    dtype: str
    source: str
    derivation: str
    null_policy: str
    finite_check: str
    latency_bucket: str
    atomization: str
    convexity_note: str
    default_off: bool = True
    selection_effect: bool = False
    future_outcome_leakage: bool = False
    requires_dp_modification: bool = False


PAYLOAD_FIELDS: tuple[PayloadFieldSpec, ...] = (
    PayloadFieldSpec(
        name="candidate_first_signal_arrival_time_s",
        family="traffic_signal_phase_timing_or_right_of_way_state",
        shape="[K]",
        dtype="float32_or_null",
        source="fixed DP candidates plus current route/signal geometry",
        derivation=(
            "first candidate support time that reaches the current route signal "
            "control region; null if no relevant signal/control region is visible"
        ),
        null_policy="fail closed with traffic_signal_context_available=false",
        finite_check="finite and >= 0 for every non-null candidate value",
        latency_bucket="latency_ms_external_context_traffic_signal_payload",
        atomization=(
            "nonnegative arrival-time and missing-context indicators may become "
            "fixed coefficients a_k after a later atom gate"
        ),
        convexity_note="fixed per-candidate coefficients keep score_k(w)=a_k^T w affine",
    ),
    PayloadFieldSpec(
        name="candidate_signal_phase_change_margin_s",
        family="traffic_signal_phase_timing_or_right_of_way_state",
        shape="[K]",
        dtype="float32_or_null",
        source="TrafficLightController current _GroupState duration and last_change_time",
        derivation=(
            "current-phase remaining time minus candidate arrival time for the "
            "matched route signal; does not read realized closed-loop outcome"
        ),
        null_policy=(
            "null when controller state, group id, or arrival time is unavailable; "
            "payload reports fail_closed_reason"
        ),
        finite_check="finite signed value; downstream atom must use signed-split parts",
        latency_bucket="latency_ms_external_context_traffic_signal_payload",
        atomization=(
            "signed-split early/late phase-margin residuals, or a nonnegative "
            "unsafe-arrival hinge, may be fixed coefficients a_k"
        ),
        convexity_note=(
            "the hinge/signed split is computed before selection; the master only "
            "sees fixed coefficients and remains convex"
        ),
    ),
    PayloadFieldSpec(
        name="candidate_right_of_way_blocked_indicator",
        family="traffic_signal_phase_timing_or_right_of_way_state",
        shape="[K]",
        dtype="float32_or_null",
        source="current traffic-light phase plus candidate signal-arrival context",
        derivation=(
            "1.0 when the candidate reaches a matched signal while current-tick "
            "right-of-way context blocks passage, else 0.0"
        ),
        null_policy="null and fail-closed when signal context is unavailable",
        finite_check="each non-null value in {0.0, 1.0}",
        latency_bucket="latency_ms_external_context_traffic_signal_payload",
        atomization="nonnegative blocked-passage indicator can be a fixed atom",
        convexity_note=(
            "binary coefficient is fixed before CAMP optimization, so the "
            "score remains affine and the robust master remains convex"
        ),
    ),
    PayloadFieldSpec(
        name="candidate_route_speed_limit_min_mps",
        family="route_speed_limit_and_control_context",
        shape="[K]",
        dtype="float32_or_null",
        source="route_lanes_speed_limit and route_lanes_has_speed_limit",
        derivation="minimum valid route speed limit along the candidate support prefix",
        null_policy="null when no route speed limit is available on the support prefix",
        finite_check="finite and >= 0 for every non-null candidate value",
        latency_bucket="latency_ms_external_context_route_speed_payload",
        atomization=(
            "nonnegative missing-limit or low-limit context coefficients may "
            "condition later speed-excess atoms"
        ),
        convexity_note=(
            "route speed context is fixed at the current tick and only enters "
            "the affine score as a coefficient"
        ),
    ),
    PayloadFieldSpec(
        name="candidate_speed_limit_excess_integral_mps",
        family="route_speed_limit_and_control_context",
        shape="[K]",
        dtype="float32_or_null",
        source="candidate prefix speeds joined to current route speed limits",
        derivation=(
            "sum over support prefix of max(candidate_speed - route_speed_limit, 0)"
        ),
        null_policy="null and fail-closed when speed-limit context is unavailable",
        finite_check="finite and >= 0 for every non-null candidate value",
        latency_bucket="latency_ms_external_context_route_speed_payload",
        atomization="nonnegative speed-limit-excess integral can be a fixed atom",
        convexity_note=(
            "the max is evaluated before selection; score remains affine in w"
        ),
    ),
    PayloadFieldSpec(
        name="candidate_speed_limit_available_fraction",
        family="route_speed_limit_and_control_context",
        shape="[K]",
        dtype="float32",
        source="route_lanes_has_speed_limit joined to candidate support prefix",
        derivation="fraction of support points with valid route speed-limit context",
        null_policy="0.0 when no support point has a valid speed limit",
        finite_check="finite value in [0, 1] for every candidate",
        latency_bucket="latency_ms_external_context_route_speed_payload",
        atomization="nonnegative missing-context guard coefficient if later needed",
        convexity_note=(
            "availability metadata is fixed before selection and preserves an "
            "affine score with a convex master"
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Design-only plan for default-off external-context payloads after "
            "the external source visibility inventory."
        )
    )
    parser.add_argument("--inventory_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        inventory=_load_json(args.inventory_json),
        label=args.label,
        paths={"inventory_json": str(args.inventory_json)},
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))


def build_report(
    *,
    inventory: dict[str, Any],
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = _source_gate(inventory)
    field_reports = [_field_report(field) for field in PAYLOAD_FIELDS]
    family_reports = _family_reports(field_reports)
    checks = [
        *_source_checks(source),
        *_field_checks(field_reports, family_reports),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_external_context_payload_design_v1",
            "label": label,
            "role": (
                "design-only gate for default-off current-tick external-context "
                "payloads after source visibility inventory"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used": False,
            "paths": paths or {},
            "math_boundary": (
                "This plan defines payload fields only. It does not implement "
                "runtime logging, create atoms, train CAMP, replay closed loop, "
                "or change selection. Any future atom must be a fixed "
                "current-tick finite-candidate coefficient a_k, nonnegative or "
                "signed-split, preserving affine score_k(w)=a_k^T w and the "
                "convex simplex/CVaR/L2 master. No DP-side classical Benders "
                "master/subproblem, dual, or cut is constructed."
            ),
        },
        "source_inventory_gate": source,
        "field_specs": field_reports,
        "family_reports": family_reports,
        "design_checks": checks,
        "implementation_contract": _implementation_contract(),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed),
    }


def _source_gate(inventory: dict[str, Any]) -> dict[str, Any]:
    final = inventory.get("final_decision") or {}
    conflicts = [key for key in BLOCKED_ACTIONS if bool(final.get(key))]
    candidates = list(final.get("design_candidate_names") or [])
    missing = [name for name in REQUIRED_DESIGN_CANDIDATES if name not in candidates]
    return {
        "status": final.get("status"),
        "passed": bool(final.get("passed")),
        "authorized_next_work": final.get("authorized_next_work"),
        "design_candidate_names": candidates,
        "missing_required_design_candidates": missing,
        "blocked_action_conflicts": conflicts,
    }


def _field_report(field: PayloadFieldSpec) -> dict[str, Any]:
    row = asdict(field)
    atom = field.atomization.lower()
    convex = field.convexity_note.lower()
    row["math_checks"] = {
        "default_off": field.default_off,
        "selection_effect_free": not field.selection_effect,
        "no_future_outcome_leakage": not field.future_outcome_leakage,
        "no_dp_modification": not field.requires_dp_modification,
        "candidate_shaped": field.shape.startswith("[K]"),
        "has_latency_bucket": field.latency_bucket.startswith("latency_ms_"),
        "atomization_nonnegative_or_signed_split": (
            "nonnegative" in atom or "signed-split" in atom
        ),
        "affine_or_convex_note": "affine" in convex or "convex" in convex,
    }
    row["passed"] = all(row["math_checks"].values())
    return row


def _family_reports(fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for family in REQUIRED_DESIGN_CANDIDATES:
        family_fields = [field for field in fields if field["family"] == family]
        rows.append(
            {
                "family": family,
                "field_count": len(family_fields),
                "passed": bool(family_fields) and all(field["passed"] for field in family_fields),
                "field_names": [field["name"] for field in family_fields],
            }
        )
    return rows


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status_ready", source["status"], SOURCE_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_payload_design",
            source["authorized_next_work"],
            SOURCE_NEXT_WORK,
        ),
        _check_empty(
            "source_has_required_design_candidates",
            source["missing_required_design_candidates"],
        ),
        _check_empty("source_has_no_blocked_action_conflicts", source["blocked_action_conflicts"]),
    ]


def _field_checks(
    fields: list[dict[str, Any]],
    families: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "name": "all_payload_fields_pass_math_contract",
            "passed": all(field["passed"] for field in fields),
            "failed_fields": [field["name"] for field in fields if not field["passed"]],
        },
        {
            "name": "all_required_families_have_fields",
            "passed": all(family["passed"] for family in families),
            "failed_families": [
                family["family"] for family in families if not family["passed"]
            ],
        },
    ]


def _implementation_contract() -> dict[str, Any]:
    return {
        "allowed_next": [
            "default-off CLI flag and summary metadata",
            "payload construction helpers with synthetic unit tests",
            "null/fail-closed behavior tests",
            "latency bucket plumbing tests",
            "baseline equivalence tests proving logging has no selection effect",
        ],
        "blocked_until_later_gate": [
            "closed-loop smoke",
            "new replay matrix",
            "online selector changes",
            "CAMP retraining",
            "Full36",
            "formal seeds",
            "DP source or weight modification",
        ],
        "payload_must_include": [
            "schema_version",
            "enabled",
            "default_off",
            "selection_effect=false",
            "future_outcome_leakage=false",
            "source_available",
            "candidate_count",
            "field_shapes",
            "finite_checks",
            "fail_closed_reason",
            "latency_ms_external_context_*",
        ],
    }


def _final_decision(passed: bool) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else BLOCKED_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "next_step": (
            "Implement default-off external-context payload construction and "
            "unit tests only. Do not run replay, train, or promote selection."
            if passed
            else "Fix the source inventory or payload design contract before implementation."
        ),
        **{key: False for key in BLOCKED_ACTIONS},
    }


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# DP-CAMP External Context Payload Design",
        "",
        f"- Label: `{report['analysis'].get('label')}`",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Next step: {decision['next_step']}",
        "",
        "## Payload Fields",
        "",
        "| Field | Family | Shape | Null Policy | Latency Bucket |",
        "| --- | --- | --- | --- | --- |",
    ]
    for field in report["field_specs"]:
        lines.append(
            f"| `{field['name']}` | `{field['family']}` | `{field['shape']}` | "
            f"{field['null_policy']} | `{field['latency_bucket']}` |"
        )
    lines.extend(
        [
            "",
            "## Family Coverage",
            "",
            "| Family | Field Count | Passed |",
            "| --- | ---: | ---: |",
        ]
    )
    for family in report["family_reports"]:
        lines.append(
            f"| `{family['family']}` | `{family['field_count']}` | `{family['passed']}` |"
        )
    lines.extend(
        [
            "",
            "## Implementation Contract",
            "",
            "- Allowed next: "
            + ", ".join(f"`{item}`" for item in report["implementation_contract"]["allowed_next"]),
            "- Blocked until later gate: "
            + ", ".join(
                f"`{item}`"
                for item in report["implementation_contract"]["blocked_until_later_gate"]
            ),
            "",
            "## Mathematical Boundary",
            "",
            report["analysis"]["math_boundary"],
            "",
            "This is a finite-candidate payload design gate, not replay, not "
            "training, not selector promotion, and not a classical Benders "
            "decomposition.",
            "",
        ]
    )
    return "\n".join(lines)


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": observed == expected,
        "observed": observed,
        "expected": expected,
    }


def _check_empty(name: str, observed: list[Any]) -> dict[str, Any]:
    return {"name": name, "passed": not observed, "observed": observed}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


if __name__ == "__main__":
    main()
