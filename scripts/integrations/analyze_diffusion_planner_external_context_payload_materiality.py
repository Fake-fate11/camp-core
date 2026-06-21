#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


RESULT_READY_STATUS = "external_context_payload_smoke_result_ready"
RESULT_NEXT_WORK = "external_context_payload_materiality_diagnosis_existing_smoke_only"
READY_STATUS = "external_context_payload_materiality_ready"
REJECT_STATUS = "external_context_payload_materiality_rejected"
AUTHORIZED_NEXT_WORK = "external_context_payload_atomization_preflight_existing_smoke_only"
LOG_NAME = "camp_selection_log.json"

TRAFFIC_SIGNAL_FIELDS = (
    "candidate_first_signal_arrival_time_s",
    "candidate_signal_phase_change_margin_s",
    "candidate_right_of_way_blocked_indicator",
)
ROUTE_SPEED_FIELDS = (
    "candidate_route_speed_limit_min_mps",
    "candidate_speed_limit_excess_integral_mps",
    "candidate_speed_limit_available_fraction",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only materiality diagnosis for external-context payload smoke "
            "logs. It consumes existing logs only; it does not run Diffusion "
            "Planner or train CAMP."
        )
    )
    parser.add_argument("--smoke_result_json", type=Path, required=True)
    parser.add_argument("--candidate_root", type=Path, required=True)
    parser.add_argument("--expected_records", type=int, default=3)
    parser.add_argument("--expected_candidates", type=int, default=8)
    parser.add_argument("--variation_epsilon", type=float, default=1e-9)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        smoke_result=_load_json(args.smoke_result_json),
        candidate_root=args.candidate_root,
        expected_records=args.expected_records,
        expected_candidates=args.expected_candidates,
        variation_epsilon=args.variation_epsilon,
        label=args.label,
        paths={
            "smoke_result_json": str(args.smoke_result_json),
            "candidate_root": str(args.candidate_root),
        },
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    if args.require_pass and not report["final_decision"]["passed"]:
        raise SystemExit(1)


def analyze(
    *,
    smoke_result: dict[str, Any],
    candidate_root: Path,
    expected_records: int = 3,
    expected_candidates: int = 8,
    variation_epsilon: float = 1e-9,
    label: str | None = None,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    if expected_records <= 0:
        raise ValueError("expected_records must be positive.")
    if expected_candidates <= 0:
        raise ValueError("expected_candidates must be positive.")
    if variation_epsilon < 0.0:
        raise ValueError("variation_epsilon must be nonnegative.")

    logs = _load_selection_logs(candidate_root)
    records = [record for _, rows in logs for record in rows]
    result_checks = _result_checks(smoke_result)
    record_checks = _record_checks(
        records,
        expected_records=expected_records,
        expected_candidates=expected_candidates,
    )
    field_reports = _field_reports(records, variation_epsilon=variation_epsilon)
    family_reports = _family_reports(field_reports)
    material_families = [
        family["family"] for family in family_reports if family["material"]
    ]
    passed = (
        all(check["passed"] for check in result_checks)
        and all(check["passed"] for check in record_checks)
        and bool(material_families)
    )
    return {
        "analysis": {
            "name": "dp_camp_external_context_payload_materiality_v1",
            "label": label,
            "role": (
                "read-only materiality diagnosis over existing external-context "
                "payload smoke logs"
            ),
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used": False,
            "formal_seed_records": 0,
            "variation_epsilon": float(variation_epsilon),
            "paths": paths or {},
            "math_boundary": (
                "This diagnosis reads fixed current-tick finite-candidate "
                "payload coefficients from already generated smoke logs. It "
                "does not create atoms, train CAMP, execute DP, or authorize "
                "new replay. A future atomization gate may use only fixed "
                "nonnegative or signed-split candidate coefficients so CAMP "
                "score remains score_k(w)=a_k^T w and the simplex/CVaR/L2 "
                "master remains convex. No classical Benders claim is made."
            ),
        },
        "result_gate_checks": result_checks,
        "record_checks": record_checks,
        "field_reports": field_reports,
        "family_reports": family_reports,
        "material_families": material_families,
        "accept_criteria": [
            "previous smoke result gate passed and authorized existing-smoke materiality diagnosis",
            "candidate logs contain the expected number of records and candidates",
            "payloads remain no-leak and selection-effect-free",
            "at least one external-context family has candidate-level nonconstant or nonzero materiality",
        ],
        "reject_criteria": [
            "previous smoke result gate is missing or rejected",
            "candidate logs are missing, wrong-sized, leaky, or selection-effectful",
            "all external-context fields are unavailable or constant with no nonzero risk signal",
            "the diagnosis requests new replay, online selection, CAMP retraining, DP modification, Full36, or formal seeds",
        ],
        "final_decision": {
            "status": READY_STATUS if passed else REJECT_STATUS,
            "passed": passed,
            "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
            "closed_loop_replay_authorized": False,
            "new_replay_authorized": False,
            "full36_authorized": False,
            "Full36_authorized": False,
            "formal_seeds_authorized": False,
            "online_selector_authorized": False,
            "camp_retraining_authorized": False,
            "CAMP_retraining_authorized": False,
            "dp_modification_authorized": False,
            "DP_modification_authorized": False,
            "classic_benders_claim_authorized": False,
            "next_step": (
                "Design an atomization preflight using only the material "
                "existing-smoke external-context fields."
                if passed
                else "Reject external-context atomization from this smoke and inspect materiality gaps."
            ),
        },
    }


def _result_checks(smoke_result: dict[str, Any]) -> list[dict[str, Any]]:
    decision = smoke_result.get("final_decision") or {}
    return [
        _check_equal("result_gate_status_ready", decision.get("status"), RESULT_READY_STATUS),
        _check_equal("result_gate_passed", decision.get("passed"), True),
        _check_equal(
            "result_gate_authorizes_materiality",
            decision.get("authorized_next_work"),
            RESULT_NEXT_WORK,
        ),
        _check_equal("result_gate_no_new_replay", decision.get("new_replay_authorized"), False),
        _check_equal("result_gate_no_training", decision.get("camp_retraining_authorized"), False),
        _check_equal("result_gate_no_formal", decision.get("formal_seeds_authorized"), False),
    ]


def _record_checks(
    records: list[dict[str, Any]],
    *,
    expected_records: int,
    expected_candidates: int,
) -> list[dict[str, Any]]:
    checks = [
        _check_equal("record_count", len(records), expected_records),
    ]
    payload_records = 0
    for index, record in enumerate(records):
        payload = record.get("external_context_payload_logging")
        present = isinstance(payload, dict)
        checks.append(_check_equal(f"record_{index}_payload_present", present, True))
        if not present:
            continue
        payload_records += 1
        checks.extend(
            [
                _check_equal(
                    f"record_{index}_candidate_count",
                    int(payload.get("candidate_count", -1)),
                    expected_candidates,
                ),
                _check_equal(
                    f"record_{index}_selection_effect",
                    payload.get("selection_effect"),
                    False,
                ),
                _check_equal(
                    f"record_{index}_future_outcome_leakage",
                    payload.get("future_outcome_leakage"),
                    False,
                ),
                _check_equal(
                    f"record_{index}_closed_loop_outcome_fields_read",
                    payload.get("closed_loop_outcome_fields_read"),
                    False,
                ),
                _check_equal(
                    f"record_{index}_closed_loop_outcomes_absent",
                    record.get("candidate_closed_loop_outcomes"),
                    None,
                ),
            ]
        )
    checks.append(_check_equal("payload_record_count", payload_records, expected_records))
    return checks


def _field_reports(
    records: list[dict[str, Any]],
    *,
    variation_epsilon: float,
) -> list[dict[str, Any]]:
    reports = []
    for family, fields in (
        ("traffic_signal", TRAFFIC_SIGNAL_FIELDS),
        ("route_speed", ROUTE_SPEED_FIELDS),
    ):
        for field in fields:
            rows = []
            finite_values = []
            material_records = 0
            nonzero_records = 0
            varying_records = 0
            for record in records:
                payload = record.get("external_context_payload_logging")
                values = None if not isinstance(payload, dict) else payload.get(field)
                array = _finite_array(values)
                if array.size:
                    finite_values.extend(float(value) for value in array)
                    span = float(np.max(array) - np.min(array))
                    nonzero = bool(np.any(np.abs(array) > variation_epsilon))
                    varying = span > variation_epsilon
                    material = nonzero or varying
                    nonzero_records += int(nonzero)
                    varying_records += int(varying)
                    material_records += int(material)
                    rows.append(
                        {
                            "finite_count": int(array.size),
                            "span": span,
                            "nonzero": nonzero,
                            "varying": varying,
                            "material": material,
                        }
                    )
                else:
                    rows.append(
                        {
                            "finite_count": 0,
                            "span": 0.0,
                            "nonzero": False,
                            "varying": False,
                            "material": False,
                        }
                    )
            material = _field_material(field, material_records, nonzero_records, varying_records)
            reports.append(
                {
                    "family": family,
                    "field": field,
                    "records": len(records),
                    "records_with_finite_values": sum(
                        1 for row in rows if row["finite_count"] > 0
                    ),
                    "material_records": material_records,
                    "nonzero_records": nonzero_records,
                    "varying_records": varying_records,
                    "finite_min": min(finite_values) if finite_values else None,
                    "finite_max": max(finite_values) if finite_values else None,
                    "record_reports": rows,
                    "material": material,
                }
            )
    return reports


def _field_material(
    field: str,
    material_records: int,
    nonzero_records: int,
    varying_records: int,
) -> bool:
    if field == "candidate_route_speed_limit_min_mps":
        return False
    if field == "candidate_speed_limit_available_fraction":
        return varying_records > 0
    return material_records > 0 or nonzero_records > 0


def _family_reports(field_reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    families = []
    for family in ("traffic_signal", "route_speed"):
        fields = [report for report in field_reports if report["family"] == family]
        material_fields = [report["field"] for report in fields if report["material"]]
        families.append(
            {
                "family": family,
                "material": bool(material_fields),
                "material_fields": material_fields,
                "fields_with_finite_values": [
                    report["field"]
                    for report in fields
                    if report["records_with_finite_values"] > 0
                ],
            }
        )
    return families


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# External Context Payload Materiality",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- New replay authorized: `{decision['new_replay_authorized']}`",
        "",
        "## Material Families",
        "",
    ]
    for family in report["family_reports"]:
        lines.append(
            f"- `{family['family']}`: material=`{family['material']}`, "
            f"fields=`{family['material_fields']}`"
        )
    lines.extend(["", "## Field Reports", ""])
    for field in report["field_reports"]:
        lines.append(
            f"- `{field['field']}`: finite_records="
            f"`{field['records_with_finite_values']}`, material_records="
            f"`{field['material_records']}`, material=`{field['material']}`"
        )
    lines.extend(["", "## Math Boundary", "", report["analysis"]["math_boundary"], ""])
    return "\n".join(lines)


def _load_selection_logs(root: Path) -> list[tuple[Path, list[dict[str, Any]]]]:
    if not root.is_dir():
        raise FileNotFoundError(f"candidate_root does not exist: {root}")
    paths = sorted(root.rglob(LOG_NAME))
    if not paths:
        raise FileNotFoundError(f"No {LOG_NAME} found under {root}")
    logs = []
    for path in paths:
        payload = _load_json(path)
        if not isinstance(payload, list):
            raise ValueError(f"{path} must contain a JSON list.")
        if not all(isinstance(record, dict) for record in payload):
            raise ValueError(f"{path} records must be JSON objects.")
        logs.append((path, payload))
    return logs


def _finite_array(values: Any) -> np.ndarray:
    if values is None:
        return np.asarray([], dtype=np.float64)
    array = np.asarray(
        [np.nan if value is None else value for value in values],
        dtype=np.float64,
    ).reshape(-1)
    return array[np.isfinite(array)]


def _check_equal(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": actual == expected,
        "actual": actual,
        "expected": expected,
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
