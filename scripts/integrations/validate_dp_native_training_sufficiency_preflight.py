#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.validate_dp_native_training_data_contract import (  # noqa: E402
    validate_record,
)


SCHEMA_VERSION = "dp_native_training_sufficiency_preflight_v1"
PROFILE = "development_minimal_v1"
FORMAL_SEEDS = {11, 12, 13}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only DP-native training sufficiency preflight. This checks "
            "coverage, clean provenance, label availability, and split "
            "shape before any later training request. It does not run replay, "
            "generate candidates, train CAMP, or modify DP."
        )
    )
    parser.add_argument("--selection_log", type=Path, action="append", required=True)
    parser.add_argument(
        "--label_source",
        choices=("dp_reward", "closed_loop_outcome", "safety_cost_v1_hard_guarded"),
        required=True,
    )
    parser.add_argument("--reward_key", default="quality_without_progress")
    parser.add_argument("--reward_progress_weight", type=float, default=2.0)
    parser.add_argument("--min_records", type=int, default=100)
    parser.add_argument("--min_routes", type=int, default=3)
    parser.add_argument("--min_seeds", type=int, default=4)
    parser.add_argument("--min_traffic_light_states", type=int, default=2)
    parser.add_argument("--min_candidate_count", type=int, default=2)
    parser.add_argument("--require_heldout_split", action="store_true")
    parser.add_argument("--allow_formal_seeds", action="store_true")
    parser.add_argument("--output_json", type=Path, default=None)
    parser.add_argument("--output_md", type=Path, default=None)
    return parser.parse_args(argv)


def _records_from_path(path: Path) -> tuple[Path, list[dict[str, Any]]]:
    log_path = path / "camp_selection_log.json" if path.is_dir() else path
    if not log_path.is_file():
        raise FileNotFoundError(f"Selection log not found: {log_path}")
    records = json.loads(log_path.read_text(encoding="utf-8"))
    if not isinstance(records, list) or not all(
        isinstance(record, dict) for record in records
    ):
        raise ValueError(f"{log_path} must contain a JSON object list.")
    return log_path, records


def _metadata_from_log_path(path: Path) -> dict[str, Any]:
    name = path.parent.name if path.name == "camp_selection_log.json" else path.stem
    seed_match = re.search(r"(?:^|_)seed(\d+)(?:_|$)", name)
    tl_match = re.search(r"(?:^|_)tl_(on|off)(?:_|$)", name)
    route = name
    if seed_match:
        route = name[: seed_match.start()].rstrip("_")
    return {
        "route": route or "unknown",
        "seed": int(seed_match.group(1)) if seed_match else None,
        "traffic_lights": tl_match.group(1) if tl_match else None,
        "group_name": name,
    }


def _candidate_count(record: dict[str, Any]) -> int:
    atoms = record.get("atoms")
    return len(atoms) if isinstance(atoms, list) else 0


def _dp_reward_record_errors(
    record: dict[str, Any],
    *,
    reward_key: str,
) -> list[str]:
    candidate_count = _candidate_count(record)
    rewards = record.get("dp_candidate_rewards")
    if not isinstance(rewards, list):
        return ["dp_candidate_rewards_missing"]
    errors: list[str] = []
    if len(rewards) != candidate_count:
        errors.append("dp_candidate_rewards_candidate_count_mismatch")
    for index, reward in enumerate(rewards):
        if not isinstance(reward, dict):
            errors.append(f"dp_candidate_reward_{index}_not_object")
            continue
        if reward_key == "quality_without_progress":
            if "total" not in reward or "progress" not in reward:
                errors.append(f"dp_candidate_reward_{index}_missing_total_or_progress")
        elif reward_key not in reward:
            errors.append(f"dp_candidate_reward_{index}_missing_{reward_key}")
    return errors


def _outcome_label_record_errors(record: dict[str, Any]) -> list[str]:
    candidate_count = _candidate_count(record)
    outcomes = record.get("candidate_closed_loop_outcomes")
    if not isinstance(outcomes, list):
        return ["candidate_closed_loop_outcomes_missing"]
    if len(outcomes) != candidate_count:
        return ["candidate_closed_loop_outcomes_candidate_count_mismatch"]
    return []


def _label_record_errors(
    record: dict[str, Any],
    *,
    label_source: str,
    reward_key: str,
) -> list[str]:
    if label_source == "dp_reward":
        return _dp_reward_record_errors(record, reward_key=reward_key)
    return _outcome_label_record_errors(record)


def evaluate_training_sufficiency(
    paths: list[Path],
    *,
    label_source: str,
    reward_key: str = "quality_without_progress",
    min_records: int = 100,
    min_routes: int = 3,
    min_seeds: int = 4,
    min_traffic_light_states: int = 2,
    min_candidate_count: int = 2,
    require_heldout_split: bool = False,
    allow_formal_seeds: bool = False,
) -> dict[str, Any]:
    loaded_logs: list[str] = []
    failed_records: list[dict[str, Any]] = []
    label_failed_records: list[dict[str, Any]] = []
    routes: Counter[str] = Counter()
    seeds: Counter[str] = Counter()
    traffic_lights: Counter[str] = Counter()
    candidate_counts: Counter[str] = Counter()
    group_counts: Counter[str] = Counter()
    formal_seed_records = 0
    record_count = 0

    for path in paths:
        log_path, records = _records_from_path(path)
        loaded_logs.append(str(log_path))
        meta = _metadata_from_log_path(log_path)
        route = str(meta["route"])
        seed = meta["seed"]
        tl_state = meta["traffic_lights"]
        for record_index, record in enumerate(records):
            record_count += 1
            routes[route] += 1
            group_counts[str(meta["group_name"])] += 1
            if seed is not None:
                seeds[str(seed)] += 1
                if int(seed) in FORMAL_SEEDS:
                    formal_seed_records += 1
            if tl_state is not None:
                traffic_lights[str(tl_state)] += 1
            candidate_counts[str(_candidate_count(record))] += 1

            contract_errors = validate_record(record)
            if contract_errors:
                failed_records.append(
                    {
                        "log_path": str(log_path),
                        "record_index": int(record_index),
                        "errors": sorted(set(contract_errors)),
                    }
                )
            label_errors = _label_record_errors(
                record,
                label_source=label_source,
                reward_key=reward_key,
            )
            if label_errors:
                label_failed_records.append(
                    {
                        "log_path": str(log_path),
                        "record_index": int(record_index),
                        "errors": sorted(set(label_errors)),
                    }
                )

    checks = {
        "records_at_least_min": record_count >= int(min_records),
        "routes_at_least_min": len(routes) >= int(min_routes),
        "seeds_at_least_min": len(seeds) >= int(min_seeds),
        "traffic_light_states_at_least_min": (
            len(traffic_lights) >= int(min_traffic_light_states)
        ),
        "candidate_count_at_least_min": all(
            int(count) >= int(min_candidate_count) for count in candidate_counts
        )
        if candidate_counts
        else False,
        "clean_contract_passed": not failed_records and record_count > 0,
        "label_source_records_present": not label_failed_records and record_count > 0,
        "formal_seeds_absent_or_allowed": allow_formal_seeds
        or formal_seed_records == 0,
        "heldout_split_possible": (
            (len(routes) >= 2 or len(seeds) >= 2)
            if require_heldout_split
            else True
        ),
    }
    failed_checks = [name for name, passed in checks.items() if not passed]
    passed = not failed_checks
    return {
        "schema_version": SCHEMA_VERSION,
        "profile": PROFILE,
        "selection_logs": loaded_logs,
        "label_source": label_source,
        "reward_key": reward_key if label_source == "dp_reward" else None,
        "thresholds": {
            "min_records": int(min_records),
            "min_routes": int(min_routes),
            "min_seeds": int(min_seeds),
            "min_traffic_light_states": int(min_traffic_light_states),
            "min_candidate_count": int(min_candidate_count),
            "require_heldout_split": bool(require_heldout_split),
            "allow_formal_seeds": bool(allow_formal_seeds),
        },
        "records": int(record_count),
        "routes": dict(sorted(routes.items())),
        "seeds": dict(sorted(seeds.items())),
        "traffic_lights": dict(sorted(traffic_lights.items())),
        "candidate_count_values": dict(sorted(candidate_counts.items())),
        "groups": dict(sorted(group_counts.items())),
        "formal_seed_records": int(formal_seed_records),
        "checks": checks,
        "failed_checks": failed_checks,
        "failed_records": failed_records,
        "label_failed_records": label_failed_records,
        "passed": bool(passed),
        "read_only": True,
        "default_off_preflight": True,
        "replay_executed": False,
        "candidate_generation_executed": False,
        "training_execution_authorized": False,
        "camp_retraining_authorized": False,
        "deployable_checkpoint_claim_authorized": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "dp_modification_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# DP Native Training Sufficiency Preflight",
        "",
        f"- Passed: `{report['passed']}`",
        f"- Profile: `{report['profile']}`",
        f"- Records: `{report['records']}`",
        f"- Label source: `{report['label_source']}`",
        f"- Failed checks: `{', '.join(report['failed_checks'])}`",
        f"- Replay executed: `{report['replay_executed']}`",
        f"- Candidate generation executed: `{report['candidate_generation_executed']}`",
        f"- Training execution authorized: `{report['training_execution_authorized']}`",
        "",
        "## Coverage",
        "",
        "```json",
        json.dumps(
            {
                "routes": report["routes"],
                "seeds": report["seeds"],
                "traffic_lights": report["traffic_lights"],
                "candidate_count_values": report["candidate_count_values"],
            },
            indent=2,
            sort_keys=True,
        ),
        "```",
        "",
    ]
    if report["failed_records"] or report["label_failed_records"]:
        lines.extend(["## Failed Records", ""])
        for row in report["failed_records"][:20]:
            lines.append(
                f"- `{row['log_path']}` record `{row['record_index']}`: "
                + ", ".join(f"`{error}`" for error in row["errors"])
            )
        for row in report["label_failed_records"][:20]:
            lines.append(
                f"- `{row['log_path']}` record `{row['record_index']}` labels: "
                + ", ".join(f"`{error}`" for error in row["errors"])
            )
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = evaluate_training_sufficiency(
        args.selection_log,
        label_source=args.label_source,
        reward_key=args.reward_key,
        min_records=args.min_records,
        min_routes=args.min_routes,
        min_seeds=args.min_seeds,
        min_traffic_light_states=args.min_traffic_light_states,
        min_candidate_count=args.min_candidate_count,
        require_heldout_split=args.require_heldout_split,
        allow_formal_seeds=args.allow_formal_seeds,
    )
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(
            json.dumps(report, indent=2) + "\n",
            encoding="utf-8",
        )
    if args.output_md is not None:
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
