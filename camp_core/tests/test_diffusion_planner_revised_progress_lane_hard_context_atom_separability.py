from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from camp_core.integrations.diffusion_planner_progress_lane_hard_context import (
    PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION,
    PROGRESS_LANE_HARD_CONTEXT_REVISED_ATOM_NAMES,
    PROGRESS_LANE_HARD_CONTEXT_REVISED_ATOM_SCHEMA_VERSION,
)
from scripts.integrations.analyze_diffusion_planner_revised_progress_lane_hard_context_atom_separability import (
    MISSING_OUTCOMES_NEXT_WORK,
    MISSING_OUTCOMES_STATUS,
    READY_STATUS,
    SOURCE_BLOCKED_STATUS,
    analyze,
    analyze_records,
)


def _source_smoke(
    status: str = "progress_lane_hard_context_logging_smoke_passed",
) -> dict:
    return {
        "final_decision": {
            "status": status,
            "passed": status == "progress_lane_hard_context_logging_smoke_passed",
            "authorized_next_work": (
                "progress_lane_hard_context_logging_smoke_result_documentation_only"
            ),
        }
    }


def _context(seed: int = 1) -> dict:
    return {
        "log_path": f"/tmp/route/seed_{seed}/camp_selection_log.json",
        "record_index": 0,
        "path_seeds": [seed],
    }


def _outcome(value: float, progress: float = 10.0, *, lane: bool = False) -> dict:
    return {
        "value": value,
        "feasible": True,
        "progress_m": progress,
        "collision": False,
        "near_miss": False,
        "lane_violation": lane,
        "red_light_violation": False,
        "mean_jerk_mps3": 0.1,
        "mean_lateral_acceleration_mps2": 0.2,
    }


def _payload(risk: float) -> dict:
    candidates = 2
    atom_count = len(PROGRESS_LANE_HARD_CONTEXT_REVISED_ATOM_NAMES)
    revised_atoms = [
        [0.0] * atom_count,
        [risk] + [0.0] * (atom_count - 1),
    ]
    return {
        "schema_version": PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "closed_loop_outcome_fields_read": False,
        "classical_benders_claim": False,
        "candidate_count": candidates,
        "finite_checks": {
            "revised_progress_lane_hard_context_atoms": True,
            "revised_progress_lane_hard_context_atoms_nonnegative": True,
        },
        "revised_progress_lane_hard_context_atom_schema_version": (
            PROGRESS_LANE_HARD_CONTEXT_REVISED_ATOM_SCHEMA_VERSION
        ),
        "revised_progress_lane_hard_context_atom_names": list(
            PROGRESS_LANE_HARD_CONTEXT_REVISED_ATOM_NAMES
        ),
        "revised_progress_lane_hard_context_atoms": revised_atoms,
    }


def _record(
    *,
    beneficial: bool,
    risk: float,
    seed: int = 1,
    with_outcomes: bool = True,
) -> dict:
    record = {
        "num_candidates": 2,
        "seed": seed,
        "progress_lane_hard_context_logging": _payload(risk),
    }
    if with_outcomes:
        candidate = _outcome(2.0 if beneficial else -2.0, lane=not beneficial)
        record["candidate_closed_loop_outcomes"] = [_outcome(0.0), candidate]
    else:
        record["candidate_closed_loop_outcomes"] = None
    return record


def test_revised_atom_separability_rejects_missing_outcomes_as_plan_gate() -> None:
    report = analyze_records(
        [
            {
                "raw": _record(beneficial=True, risk=0.1, with_outcomes=False),
                "context": _context(),
            }
        ],
        source_smoke_report=_source_smoke(),
        fail_on_formal_seeds=True,
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
    )

    assert report["final_decision"]["status"] == MISSING_OUTCOMES_STATUS
    assert report["final_decision"]["authorized_next_work"] == MISSING_OUTCOMES_NEXT_WORK
    assert report["records"]["missing_outcome_records"] == 1
    assert report["records"]["outcome_records"] == 0
    assert report["final_decision"]["new_replay_authorized"] is False
    assert report["final_decision"]["camp_retraining_authorized"] is False
    assert all(
        coverage["finite"] == coverage["total"] == 2
        for coverage in report["payload_descriptor_coverage"].values()
    )


def test_revised_atom_separability_finds_toy_separator() -> None:
    items = [
        {"raw": _record(beneficial=True, risk=0.1), "context": _context()},
        {"raw": _record(beneficial=True, risk=0.2), "context": _context()},
        {"raw": _record(beneficial=False, risk=2.0), "context": _context()},
        {"raw": _record(beneficial=False, risk=3.0), "context": _context()},
    ]

    report = analyze_records(
        items,
        source_smoke_report=_source_smoke(),
        min_beneficial_candidates=2,
        min_harmful_candidates=2,
    )

    assert report["final_decision"]["status"] == READY_STATUS
    assert report["analysis"]["future_outcome_labels_used_for_atoms"] is False
    assert report["analysis"]["thresholds_are_offline_oracle_diagnostics"] is True
    assert report["final_decision"]["online_selector_authorized"] is False
    assert report["final_decision"]["camp_retraining_authorized"] is False
    best = report["ranked_screens"][0]
    assert best["promising_screen"] is True
    assert best["harmful_block_rate"] == 1.0
    assert best["beneficial_retain_rate"] == 1.0


def test_revised_atom_separability_blocks_when_source_smoke_not_ready() -> None:
    report = analyze_records(
        [{"raw": _record(beneficial=True, risk=0.1), "context": _context()}],
        source_smoke_report=_source_smoke(
            "progress_lane_hard_context_logging_smoke_rejected"
        ),
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
    )

    assert report["final_decision"]["status"] == SOURCE_BLOCKED_STATUS
    assert report["final_decision"]["authorized_next_work"] == (
        "fix_revised_context_logging_smoke_before_separability"
    )


def test_revised_atom_separability_rejects_formal_seed_when_forbidden() -> None:
    with pytest.raises(ValueError, match="Formal seed records are forbidden"):
        analyze_records(
            [
                {
                    "raw": _record(
                        beneficial=True,
                        risk=0.1,
                        seed=11,
                        with_outcomes=False,
                    ),
                    "context": _context(seed=11),
                }
            ],
            source_smoke_report=_source_smoke(),
            fail_on_formal_seeds=True,
            min_beneficial_candidates=1,
            min_harmful_candidates=1,
        )


def test_revised_atom_descriptor_values_are_outcome_independent() -> None:
    base = _record(beneficial=True, risk=0.1)
    mutated = copy.deepcopy(base)
    mutated["candidate_closed_loop_outcomes"][1]["mean_jerk_mps3"] = 99.0

    base_report = analyze_records(
        [{"raw": base, "context": _context()}],
        source_smoke_report=_source_smoke(),
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
    )
    mutated_report = analyze_records(
        [{"raw": mutated, "context": _context()}],
        source_smoke_report=_source_smoke(),
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
    )

    assert (
        base_report["payload_descriptor_coverage"]
        == mutated_report["payload_descriptor_coverage"]
    )
    assert base_report["normalization"] == mutated_report["normalization"]
    assert base_report["single_descriptor_screens"] == mutated_report[
        "single_descriptor_screens"
    ]


def test_revised_atom_separability_cli_reports_missing_outcomes(
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "route" / "seed_1" / "camp_selection_log.json"
    log_path.parent.mkdir(parents=True)
    log_path.write_text(
        json.dumps(
            [_record(beneficial=True, risk=0.1, with_outcomes=False)]
        ),
        encoding="utf-8",
    )
    source_path = tmp_path / "source_smoke.json"
    source_path.write_text(json.dumps(_source_smoke()), encoding="utf-8")

    report = analyze(
        [tmp_path],
        source_smoke_report=json.loads(source_path.read_text(encoding="utf-8")),
        fail_on_formal_seeds=True,
        min_beneficial_candidates=1,
        min_harmful_candidates=1,
    )

    assert report["final_decision"]["status"] == MISSING_OUTCOMES_STATUS
