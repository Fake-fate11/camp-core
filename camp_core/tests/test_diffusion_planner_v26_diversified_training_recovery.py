from __future__ import annotations

import importlib
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_recovery_parser_requires_explicit_immutable_bindings() -> None:
    recovery = importlib.import_module(
        "scripts.integrations.recover_diffusion_planner_v26_diversified_training_acquisition"
    )
    args = recovery.parse_args(
        [
            "--output-dir",
            "existing-root",
            "--original-stderr-log",
            "existing.stderr.log",
            "--expected-camp-head",
            "a" * 40,
            "--expected-route-plan-sha256",
            "b" * 64,
            "--expected-stale-status-sha256",
            "c" * 64,
            "--expected-planned",
            "1783",
            "--expected-complete",
            "479",
            "--expected-failed",
            "6",
            "--expected-unattempted",
            "1298",
        ]
    )
    assert args.expected_planned == 1783
    assert args.expected_complete == 479
    assert args.expected_failed == 6
    assert args.expected_unattempted == 1298


def test_recovery_denominator_and_unattempted_ranges_are_explicit() -> None:
    recovery = importlib.import_module(
        "scripts.integrations.recover_diffusion_planner_v26_diversified_training_acquisition"
    )
    units = [
        {"terminal": {"status": "complete"}},
        {"terminal": {"status": "typed_failure"}},
        {"terminal": {"status": "unattempted"}},
        {"terminal": {"status": "unattempted"}},
    ]
    assert recovery._denominator(units) == {
        "planned": 4,
        "complete": 1,
        "failed": 1,
        "unattempted": 2,
    }
    assert recovery._contiguous_ranges([3, 4, 8]) == [[3, 4], [8, 8]]
