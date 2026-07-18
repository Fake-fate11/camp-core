#!/usr/bin/env python3
"""Independently rebuild and review the sealed A1.6.2 bounded plan."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)


SCHEMA_VERSION = "camp_dp_v25_a162_bounded_execution_plan_review_v1"
PLAN_SCHEMA_VERSION = "camp_dp_v25_a162_route_level_bounded_execution_plan_v1"
PRODUCER_SCHEMA_VERSION = "camp_dp_v25_a162_bounded_execution_preflight_v1"
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
FORMAL_ARTIFACT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_controlled_corpus_source_freeze_retry2_ff028387_"
    "20260717T140842CST"
)
FORMAL_ROOT_SHA256 = (
    "c4dbd49c5fde36302046c6386ca1b8d9cdcaa922976f08230e6227962cc1e531"
)
EXPECTED_SEED = 25001
TICKS = 64
MAX_IDENTITIES = 320


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value))


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _physical_payload(case: Mapping[str, Any], row: Mapping[str, Any]) -> dict[str, Any]:
    actor_fields = (
        "agent_type",
        "initial_heading_rad",
        "initial_xy",
        "lateral_offset_m",
        "lateral_speed_mps",
        "lateral_target_m",
        "length_m",
        "longitudinal_acceleration_mps2",
        "longitudinal_speed_mps",
        "route_normal",
        "route_tangent",
        "trigger_time_s",
        "wheelbase_m",
        "width_m",
    )
    actors = case.get("actors")
    route = case.get("route_spec")
    chain = row.get("source_chain")
    layout = row.get("id_free_tensor_layout")
    if (
        type(actors) is not list
        or type(route) is not dict
        or type(chain) is not dict
        or type(layout) is not dict
    ):
        raise ValueError("oracle physical payload input drifted")
    physical_actors = []
    for actor in actors:
        if type(actor) is not dict or any(field not in actor for field in actor_fields):
            raise ValueError("oracle actor physical payload drifted")
        physical_actors.append({field: actor[field] for field in actor_fields})
    return {
        "schema_version": "camp_dp_v25_a162_k8_relevant_physical_payload_v1",
        "family": case.get("family"),
        "tier": case.get("tier"),
        "semantic_variant": case.get("semantic_variant"),
        "parameters": case.get("parameters"),
        "actors_in_formal_order_without_ids": physical_actors,
        "signal": case.get("signal"),
        "route_spec": {
            "start_pose": route.get("start_pose"),
            "goal_pose": route.get("goal_pose"),
            "lanelet_ids": route.get("lanelet_ids"),
            "route_length_m": route.get("route_length_m"),
        },
        "route_identity_sha256": case.get("route_identity_sha256"),
        "source_map_sha256": case.get("source_map_sha256"),
        "seed": EXPECTED_SEED,
        "source_class": row.get("source_class"),
        "phase_authority_mode": row.get("phase_authority_mode"),
        "source_chain_sha256": chain.get("source_chain_sha256"),
        "id_free_tensor_layout_sha256": layout.get("layout_sha256"),
        "fixed_candidate_contract": "sequential_fixed_dp_k8_same_forward",
    }


def _oracle_plan(
    formal_train: Sequence[Mapping[str, Any]],
    source_rows: Sequence[Mapping[str, Any]],
    *,
    source_root: str,
    source_review_root: str,
) -> dict[str, Any]:
    rows = {str(row.get("scenario_id")): row for row in source_rows}
    cases = {str(case.get("scenario_id")): case for case in formal_train}
    if (
        len(rows) != len(source_rows)
        or len(cases) != len(formal_train)
        or set(rows) != set(cases)
    ):
        raise ValueError("oracle formal/source denominator drifted")
    executable = [case for case in formal_train if case.get("runner_eligible") is True]
    if len(executable) != 1500 or any(
        type(case.get("seeds")) is not list or case["seeds"] != [EXPECTED_SEED]
        for case in executable
    ):
        raise ValueError("oracle executable denominator/seed drifted")

    def tie(case: Mapping[str, Any]) -> tuple[str, str, str]:
        row = rows[str(case["scenario_id"])]
        return (
            str(row["source_chain"]["semantic_clone_sha256"]),
            str(case["route_identity_sha256"]),
            str(case["scenario_id"]),
        )

    mapped = [
        case
        for case in executable
        if rows[str(case["scenario_id"])]["source_class"] == "mapped_signal"
    ]
    no_signal = [
        case
        for case in executable
        if rows[str(case["scenario_id"])]["source_class"] == "no_signal"
    ]
    if len(mapped) != 146 or len(no_signal) != 1354:
        raise ValueError("oracle mapped/no-signal denominator drifted")
    selected = {str(case["scenario_id"]): case for case in mapped}
    cells: dict[tuple[str, str, str, str], list[Mapping[str, Any]]] = {}
    for case in no_signal:
        key = (
            str(case["family"]),
            str(case["semantic_variant"]),
            str(case["tier"]),
            str(case["source_map_sha256"]),
        )
        cells.setdefault(key, []).append(case)
    proofs = []
    for key, group in sorted(cells.items()):
        chosen = min(group, key=tie)
        selected[str(chosen["scenario_id"])] = chosen
        terminal = [case for case in group if tie(case)[:2] == tie(chosen)[:2]]
        if len(terminal) > 1:
            hashes = [
                _sha(_physical_payload(case, rows[str(case["scenario_id"])]))
                for case in terminal
            ]
            equivalent = len(set(hashes)) == 1
            if not equivalent:
                for case in terminal:
                    selected[str(case["scenario_id"])] = case
            proofs.append(
                {
                    "primary_cell": list(key),
                    "terminal_scenario_ids": sorted(
                        str(case["scenario_id"]) for case in terminal
                    ),
                    "route_identity_sha256": tie(chosen)[1],
                    "semantic_clone_sha256": tie(chosen)[0],
                    "k8_relevant_physical_payload_sha256": hashes,
                    "all_terminal_items_equivalent": equivalent,
                    "non_equivalent_items_all_included": not equivalent,
                }
            )

    def augment(field) -> None:
        universe = {field(case) for case in no_signal}
        covered = {
            field(case)
            for case in no_signal
            if str(case["scenario_id"]) in selected
        }
        for value in sorted(universe - covered):
            candidates = [case for case in no_signal if field(case) == value]
            chosen = min(candidates, key=tie)
            selected[str(chosen["scenario_id"])] = chosen

    augment(lambda case: str(case["corridor_group_sha256"]))
    augment(
        lambda case: str(
            rows[str(case["scenario_id"])]["id_free_tensor_layout"]["layout_sha256"]
        )
    )
    identity0 = executable[0]
    selected[str(identity0["scenario_id"])] = identity0
    selected_cases = sorted(selected.values(), key=tie)
    if len(selected_cases) > MAX_IDENTITIES:
        raise ValueError("oracle bounded identity cap exceeded")
    identity0_id = str(identity0["scenario_id"])
    selected_ids = [str(case["scenario_id"]) for case in selected_cases]
    sequence = [identity0_id, *[value for value in selected_ids if value != identity0_id], identity0_id]
    runs = []
    for ordinal, scenario_id in enumerate(sequence):
        case = cases[scenario_id]
        row = rows[scenario_id]
        runs.append(
            {
                "run_ordinal": ordinal,
                "scenario_id": scenario_id,
                "occurrence": "identity0_first" if ordinal == 0 else (
                    "identity0_final_repeat" if ordinal == len(sequence) - 1 else "unique_identity"
                ),
                "ticks": TICKS,
                "seed": EXPECTED_SEED,
                "source_class": row["source_class"],
                "phase_authority_mode": row["phase_authority_mode"],
                "route_identity_sha256": case["route_identity_sha256"],
                "source_map_sha256": case["source_map_sha256"],
                "semantic_clone_sha256": row["source_chain"]["semantic_clone_sha256"],
                "source_row_sha256": _sha(row),
                "k8_relevant_physical_payload_sha256": _sha(
                    _physical_payload(case, row)
                ),
            }
        )
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "status": "passed_preflight_plan_k8_execute_closed" if all(
            proof["all_terminal_items_equivalent"] for proof in proofs
        ) else "requires_ultra_review_after_non_equivalent_tie_expansion",
        "source_root_sha256": source_root,
        "source_review_root_sha256": source_review_root,
        "seed": EXPECTED_SEED,
        "ticks_per_run": TICKS,
        "unique_identity_count": len(selected_cases),
        "run_count": len(runs),
        "snapshot_capacity": len(runs) * TICKS,
        "mapped_identity_count": len(mapped),
        "no_signal_selected_count": len(selected_cases) - len(mapped),
        "identity0_scenario_id": identity0_id,
        "execution_order_contract": "identity0_first_then_remaining_unique_then_identity0_final_repeat",
        "selection_contract": "all_mapped_plus_outcome_blind_nosignal_cells_corridor_layout",
        "tie_break_contract": "semantic_clone_sha256_route_identity_sha256_scenario_id",
        "tie_equivalence_proofs": proofs,
        "runs": runs,
        "sequential_fixed_k8": True,
        "candidate0_semantics": "operational_default_alias_from_same_forward",
        "normalization_contract": "clip(raw_atoms/generation_scales,0,10)",
        "selection_eligibility": "strict_source_valid_mask",
        "tie_break_selected_index": "lowest_eligible_candidate_index",
        "microbatch_enabled": False,
        "cache_optimization_enabled": False,
        "sharding_enabled": False,
        "k8_executed": False,
        "candidate_generation_started": False,
        "model_loaded": False,
        "simulator_started": False,
        "training_executed": False,
        "calibration_executed": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def review(args: argparse.Namespace) -> dict[str, Any]:
    head = _git(ROOT, "rev-parse", "HEAD")
    if _git(ROOT, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("CAMP tracked worktree is dirty")
    if (
        _git(args.dp_repo, "rev-parse", "HEAD") != FIXED_DP_HEAD
        or _git(args.dp_repo, "status", "--porcelain")
    ):
        raise ValueError("fixed DP drifted or is not fully clean")
    artifact_seal = verify_complete_seal(
        args.plan_artifact, args.plan_root_sha256, label="A1.6.2 bounded plan"
    )
    if artifact_seal["manifest_paths"] != sorted(
        {"COMMAND", "HEADS", "bounded_execution_plan.json", "report.json", "run.exit"}
    ) or (args.plan_artifact / "run.exit").read_bytes() != b"0\n":
        raise ValueError("bounded plan inventory/exit drifted")
    source_seal = verify_complete_seal(
        args.source_artifact, args.source_root_sha256, label="A1.6.2 source"
    )
    source_review_seal = verify_complete_seal(
        args.source_review_artifact,
        args.source_review_root_sha256,
        label="A1.6.2 source review",
    )
    formal_seal = verify_complete_seal(
        FORMAL_ARTIFACT, FORMAL_ROOT_SHA256, label="V25 formal corpus"
    )
    report = _load(args.plan_artifact / "report.json")
    actual = _load(args.plan_artifact / "bounded_execution_plan.json")
    formal = _load(FORMAL_ARTIFACT / "controlled_corpus_final_plan.json")
    source_payload = _load(args.source_artifact / "route_signal_source_receipts.json")
    source_review_report = _load(args.source_review_artifact / "report.json")
    expected = _oracle_plan(
        formal["train"],
        source_payload["cases"],
        source_root=source_seal["root_sha256"],
        source_review_root=source_review_seal["root_sha256"],
    )
    expected_report_fields = {
        "schema_version", "status", "camp_source_head", "fixed_dp_head", "dp_repo",
        "formal_artifact", "formal_root_sha256", "source_artifact",
        "source_root_sha256", "source_review_artifact", "source_review_root_sha256",
        "plan_sha256", "unique_identity_count", "run_count", "snapshot_capacity",
        "tie_proof_count", "all_tie_proofs_equivalent", "k8_executed",
        "candidate_generation_started", "model_loaded", "simulator_started",
        "full_r_started", "training_executed", "calibration_executed",
        "fresh_b2_opened", "outcome_fields_consumed", "next_gate",
    }
    if (
        set(report) != expected_report_fields
        or report.get("schema_version") != PRODUCER_SCHEMA_VERSION
        or report.get("status")
        != "passed_bounded_execution_plan_preflight_k8_execute_closed"
        or report.get("camp_source_head") != head
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
        or Path(str(report.get("dp_repo"))).resolve() != args.dp_repo.resolve()
        or Path(str(report.get("formal_artifact"))).resolve() != FORMAL_ARTIFACT.resolve()
        or report.get("formal_root_sha256") != formal_seal["root_sha256"]
        or Path(str(report.get("source_artifact"))).resolve() != args.source_artifact.resolve()
        or report.get("source_root_sha256") != source_seal["root_sha256"]
        or Path(str(report.get("source_review_artifact"))).resolve()
        != args.source_review_artifact.resolve()
        or report.get("source_review_root_sha256") != source_review_seal["root_sha256"]
        or source_review_report.get("reviewed_root_sha256") != source_seal["root_sha256"]
        or _canonical_bytes(actual) != _canonical_bytes(expected)
        or report.get("plan_sha256") != _sha(actual)
        or report.get("unique_identity_count") != 243
        or report.get("run_count") != 244
        or report.get("snapshot_capacity") != 15616
        or report.get("tie_proof_count") != 4
        or report.get("all_tie_proofs_equivalent") is not True
        or any(
            report.get(field) is not False
            for field in (
                "k8_executed", "candidate_generation_started", "model_loaded",
                "simulator_started", "full_r_started", "training_executed",
                "calibration_executed", "fresh_b2_opened",
            )
        )
        or report.get("outcome_fields_consumed") != []
    ):
        raise ValueError("independent bounded plan reconstruction/review failed")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_bounded_execution_plan_review_k8_closed",
        "review_head": head,
        "fixed_dp_head": FIXED_DP_HEAD,
        "reviewed_artifact": str(args.plan_artifact.resolve()),
        "reviewed_root_sha256": artifact_seal["root_sha256"],
        "source_artifact": str(args.source_artifact.resolve()),
        "source_root_sha256": source_seal["root_sha256"],
        "source_review_artifact": str(args.source_review_artifact.resolve()),
        "source_review_root_sha256": source_review_seal["root_sha256"],
        "formal_root_sha256": formal_seal["root_sha256"],
        "unique_identity_count": 243,
        "run_count": 244,
        "snapshot_capacity": 15616,
        "tie_proof_count": 4,
        "identity0_repeat_positions": [0, 243],
        "k8_executed": False,
        "candidate_generation_started": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
        "next_gate": "ultra_read_only_a162_bounded_plan_review_before_any_k8",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-artifact", type=Path, required=True)
    parser.add_argument("--plan-root-sha256", required=True)
    parser.add_argument("--source-artifact", type=Path, required=True)
    parser.add_argument("--source-root-sha256", required=True)
    parser.add_argument("--source-review-artifact", type=Path, required=True)
    parser.add_argument("--source-review-root-sha256", required=True)
    parser.add_argument("--dp-repo", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    try:
        report = review(args)
        _write(args.output_dir / "report.json", report)
        (args.output_dir / "HEADS").write_text(
            f"camp_source_head={report['review_head']}\nfixed_dp_head={FIXED_DP_HEAD}\n",
            encoding="ascii",
        )
        (args.output_dir / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
        (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
        root = seal_artifact(args.output_dir, label="A1.6.2 bounded plan review")
        print(json.dumps({**report, "artifact_root_sha256": root}, sort_keys=True))
    except Exception:
        if not (args.output_dir / "run.exit").exists():
            (args.output_dir / "run.exit").write_text("1\n", encoding="ascii")
        raise


if __name__ == "__main__":
    main()
