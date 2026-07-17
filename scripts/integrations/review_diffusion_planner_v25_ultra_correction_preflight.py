#!/usr/bin/env python3
"""Independently review a sealed V25 S0 correction preflight artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from scripts.integrations.run_diffusion_planner_v25_controlled_scenario_phase import (  # noqa: E402
    _load_json,
    _seal,
    _verify_seal,
    _write_json,
)
from scripts.integrations.run_diffusion_planner_v25_controlled_training_corpus import (  # noqa: E402
    CORPUS_STEPS,
    SUPERSEDED_PARTIAL_CORPUS_ROOT,
    _canonical_sha256,
)


SCHEMA_VERSION = "camp_dp_v25_ultra_correction_preflight_review_v1"
SOURCE_SCHEMA_VERSION = "camp_dp_v25_ultra_correction_preflight_v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Review a sealed bounded V25 S0 correction preflight."
    )
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise FileExistsError(f"output already exists: {args.output_dir}")
    args.output_dir.mkdir(parents=True)
    try:
        report = _review(args.artifact)
        _write_json(args.output_dir / "report.json", report)
        (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
        (args.output_dir / "COMMAND").write_text(
            " ".join(sys.argv) + "\n", encoding="utf-8"
        )
        root_sha = _seal(args.output_dir)
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "output_dir": str(args.output_dir),
                    "root_sha256": root_sha,
                },
                sort_keys=True,
            )
        )
    except BaseException as exc:
        _write_json(
            args.output_dir / "failure.json",
            {
                "schema_version": SCHEMA_VERSION,
                "status": "failed",
                "failure_type": type(exc).__name__,
                "failure_reason": str(exc),
                "fresh_b_opened": False,
            },
        )
        (args.output_dir / "run.exit").write_text("1\n", encoding="ascii")
        _seal(args.output_dir)
        raise


def _review(artifact: Path) -> dict[str, Any]:
    source_root = _verify_seal(artifact)
    report = _load_json(artifact / "report.json")
    probes = _load_json(artifact / "probe_results.json")
    run_exit = (artifact / "run.exit").read_text(encoding="ascii")
    rows = probes.get("probe_results")
    if not isinstance(rows, list):
        raise ValueError("preflight probe results are missing")
    checks = {
        "source_schema": report.get("schema_version") == SOURCE_SCHEMA_VERSION,
        "source_status_passed": report.get("status") == "passed",
        "source_run_exit_zero": run_exit == "0\n",
        "source_fresh_false": report.get("fresh_b_opened") is False,
        "source_outcomes_not_consumed": report.get("outcome_fields_consumed") == [],
        "source_full_corpus_not_started": report.get("full_corpus_started") is False,
        "source_sequential_k8": report.get("sequential_k8") is True,
        "no_optimization_mixed": (
            report.get("micro_batch_used") is False
            and report.get("cache_optimization_used") is False
            and report.get("snapshot_sharding_used") is False
        ),
        "old_partial_rejected": report.get("rejected_roots")
        == [SUPERSEDED_PARTIAL_CORPUS_ROOT],
        "all_report_checks_passed": all(report.get("checks", {}).values()),
        "three_probe_denominator": len(rows) == 3,
        "all_probe_ticks_64": all(
            row.get("tick_count") == CORPUS_STEPS for row in rows
        ),
        "identity0_repeat_exact": (
            len(rows) == 3
            and rows[0].get("tick_fingerprints")
            == rows[1].get("tick_fingerprints")
        ),
        "red_easy_present": (
            len(rows) == 3
            and rows[2].get("family") == "red_light_phase_timing"
            and rows[2].get("tier") == "easy"
        ),
        "fingerprint_roots_recompute": all(
            row.get("tick_fingerprint_root_sha256")
            == _canonical_sha256(row.get("tick_fingerprints"))
            for row in rows
        ),
        "selected_sequence_roots_recompute": all(
            row.get("selected_sequence_sha256")
            == _canonical_sha256(row.get("selected_sequence"))
            for row in rows
        ),
        "all_probe_contract_checks_passed": all(
            all(
                value is True or (name == "failure_class" and value is None)
                for name, value in row.get("checks", {}).items()
            )
            for row in rows
        ),
        "heads_and_command_present": (
            (artifact / "HEADS").is_file()
            and (artifact / "COMMAND").is_file()
        ),
    }
    if not all(checks.values()):
        failed = [name for name, passed in checks.items() if not passed]
        raise ValueError("independent review failed: " + ",".join(failed))
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed",
        "reviewed_artifact": str(artifact),
        "reviewed_root_sha256": source_root,
        "checks": checks,
        "probe_count": len(rows),
        "probe_tick_count": sum(int(row["tick_count"]) for row in rows),
        "rejected_roots": [SUPERSEDED_PARTIAL_CORPUS_ROOT],
        "fresh_b_opened": False,
        "outcome_fields_consumed": [],
        "review_is_read_only": True,
    }


if __name__ == "__main__":
    main()
