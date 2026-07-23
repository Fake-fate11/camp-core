#!/usr/bin/env python3
"""Independently review a V25 calibration freeze projected from paired evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterator, Mapping


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from camp_core.integrations.diffusion_planner_v25_calibration_artifact import (  # noqa: E402
    build_calibration_freeze_payload_from_corpus,
    validate_calibration_freeze_payload,
)
from camp_core.integrations.diffusion_planner_v25_calibration_corpus import (  # noqa: E402
    project_candidate0_calibration_corpus_from_paired_terminals,
)
from camp_core.integrations.diffusion_planner_v25_calibration_preregistration import (  # noqa: E402
    validate_paired_calibration_preregistration,
)
from camp_core.integrations.diffusion_planner_v25_paired_calibration import (  # noqa: E402
    validate_paired_calibration_execution_plan,
)
from camp_core.integrations.diffusion_planner_v25_signal_complete_plan import (  # noqa: E402
    validate_signal_complete_execution_plan,
)
from scripts.integrations import review_diffusion_planner_v25_paired_calibration as paired_review  # noqa: E402


SCHEMA_VERSION = "camp_dp_v25_calibration_freeze_from_paired_review_v1"
SOURCE_SCHEMA_VERSION = "camp_dp_v25_calibration_freeze_from_paired_artifact_v1"
PROJECTION_RECEIPT_SCHEMA_VERSION = (
    "camp_dp_v25_candidate0_streaming_projection_receipt_v1"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
MAX_TERMINAL_FILE_BYTES = 256 * 1024 * 1024


def review(artifact: Path, expected_root: str) -> dict[str, Any]:
    source = artifact.resolve()
    seal = verify_complete_seal(
        source, expected_root, label="calibration freeze from paired evidence"
    )
    if set(seal["manifest_paths"]) != {
        "COMMAND",
        "HEADS",
        "calibration_freeze.json",
        "projection_receipt.json",
        "report.json",
        "run.exit",
    }:
        raise ValueError("calibration freeze-from-paired inventory drifted")
    if (source / "run.exit").read_bytes() != b"0\n":
        raise ValueError("calibration freeze-from-paired exit drifted")
    report = _canonical_json(source / "report.json")
    payload = validate_calibration_freeze_payload(
        _canonical_json(source / "calibration_freeze.json")
    )
    receipt = _canonical_json(source / "projection_receipt.json")

    raw, recovery, recovery_review, roots, base, paired, preregistration = (
        _open_accepted_paired_chain(
            paired_calibration_artifact=Path(report["paired_calibration_artifact"]),
            paired_calibration_root_sha256=report[
                "paired_calibration_root_sha256"
            ],
            recovery_artifact=Path(report["recovery_artifact"]),
            recovery_root_sha256=report["recovery_root_sha256"],
            recovery_review_artifact=Path(report["recovery_review_artifact"]),
            recovery_review_root_sha256=report["recovery_review_root_sha256"],
        )
    )
    terminals, terminal_rows = _stream_candidate0_terminals(raw, paired)
    corpus = project_candidate0_calibration_corpus_from_paired_terminals(
        calibration_plan=base,
        paired_plan=paired,
        candidate0_terminals=terminals,
    )
    root_bindings = _calibration_root_bindings(
        preregistration=preregistration,
        paired_calibration_root_sha256=report[
            "paired_calibration_root_sha256"
        ],
        recovery_review_root_sha256=report["recovery_review_root_sha256"],
        preregistration_root_sha256=roots["preregistration_root_sha256"],
    )
    models = preregistration["model_authority"]
    expected_payload = validate_calibration_freeze_payload(
        build_calibration_freeze_payload_from_corpus(
            root_bindings=root_bindings,
            calibration_corpus=corpus,
            frozen_model_registry_sha256=models["model_registry_sha256"],
            training_scale_sha256=models["training_scale_sha256"],
            context_scaler_sha256=models["context_scaler_sha256"],
        )
    )
    if not _strict_equal(payload, expected_payload):
        raise ValueError("calibration freeze differs from independent raw projection")

    resolution = payload["noninferiority_resolvability"]
    repeatability_ids = [
        row["repeatability_identity_sha256"]
        for row in payload["candidate0_rows"]
    ]
    if (
        len(repeatability_ids) != 100
        or len(set(repeatability_ids)) != 100
        or resolution["repeatability_status"]
        != "not_estimable_no_exact_candidate0_duplicates"
        or resolution["exact_duplicate_group_count"] != 0
        or resolution["repeatability_gate_blocks_fresh"] is not False
        or resolution["heterogeneity_diagnostic_only"] is not True
        or resolution["heterogeneity_may_not_gate_fresh"] is not True
    ):
        raise ValueError("candidate0 repeatability/heterogeneity classification drifted")

    expected_receipt = {
        "schema_version": PROJECTION_RECEIPT_SCHEMA_VERSION,
        "status": "passed_streaming_candidate0_projection",
        "paired_calibration_artifact": str(raw),
        "paired_calibration_root_sha256": report[
            "paired_calibration_root_sha256"
        ],
        "recovery_artifact": str(recovery),
        "recovery_root_sha256": report["recovery_root_sha256"],
        "recovery_review_artifact": str(recovery_review),
        "recovery_review_root_sha256": report["recovery_review_root_sha256"],
        "terminal_file_count": len(terminal_rows),
        "terminal_total_bytes": sum(row["size_bytes"] for row in terminal_rows),
        "maximum_terminal_file_bytes": max(
            row["size_bytes"] for row in terminal_rows
        ),
        "loader_memory_ceiling_bytes": MAX_TERMINAL_FILE_BYTES,
        "terminal_files": terminal_rows,
        "candidate0_row_count": payload["candidate0_row_count"],
        "candidate0_rows_sha256": payload["candidate0_rows_sha256"],
        "heterogeneity_definition": (
            "within_map_cross_scenario_route_semantic_block_seed_heterogeneity"
        ),
        "heterogeneity_diagnostic_only": True,
        "repeatability_identity_definition": resolution[
            "exact_duplicate_identity_contract"
        ],
        "repeatability_status": resolution["repeatability_status"],
        "exact_duplicate_group_count": 0,
        "fresh_b2_opened": False,
        "fresh_outcome_fields_consumed": [],
    }
    if (
        not _strict_equal(receipt, expected_receipt)
        or report.get("schema_version") != SOURCE_SCHEMA_VERSION
        or report.get("status") != "calibration_freeze_passed"
        or report.get("camp_head") != _heads_camp(source / "HEADS")
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
        or report.get("calibration_freeze_sha256")
        != _sha256(source / "calibration_freeze.json")
        or report.get("projection_receipt_sha256")
        != _sha256(source / "projection_receipt.json")
        or report.get("candidate0_row_count") != 100
        or report.get("heterogeneity_cluster_count") != 5
        or report.get("heterogeneity_diagnostic_only") is not True
        or report.get("repeatability_status")
        != "not_estimable_no_exact_candidate0_duplicates"
        or report.get("exact_duplicate_repeatability_group_count") != 0
        or report.get("repeatability_gate_blocks_fresh") is not False
        or report.get("margin_enlargement_authorized") is not False
        or report.get("model_or_threshold_changed") is not False
        or report.get("fresh_b2_opened") is not False
        or report.get("fresh_open_authorized") is not False
        or report.get("fresh_outcome_fields_consumed") != []
    ):
        raise ValueError("calibration freeze-from-paired report drifted")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_calibration_freeze_from_paired_review",
        "reviewed_artifact": str(source),
        "reviewed_root_sha256": seal["root_sha256"],
        "paired_calibration_root_sha256": report[
            "paired_calibration_root_sha256"
        ],
        "recovery_root_sha256": report["recovery_root_sha256"],
        "recovery_review_root_sha256": report["recovery_review_root_sha256"],
        "candidate0_row_count": 100,
        "heterogeneity_cluster_count": 5,
        "heterogeneity_diagnostic_only": True,
        "repeatability_status": (
            "not_estimable_no_exact_candidate0_duplicates"
        ),
        "exact_duplicate_repeatability_group_count": 0,
        "repeatability_gate_blocks_fresh": False,
        "calibration_status": "calibration_freeze_passed",
        "fresh_preopen_qualification_allowed": True,
        "margin_enlargement_authorized": False,
        "model_or_threshold_changed": False,
        "fresh_b2_opened": False,
        "fresh_open_authorized": False,
        "fresh_outcome_fields_consumed": [],
    }


def _open_accepted_paired_chain(
    *,
    paired_calibration_artifact: Path,
    paired_calibration_root_sha256: str,
    recovery_artifact: Path,
    recovery_root_sha256: str,
    recovery_review_artifact: Path,
    recovery_review_root_sha256: str,
) -> tuple[
    Path,
    Path,
    Path,
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    raw = paired_calibration_artifact.resolve()
    recovery = recovery_artifact.resolve()
    recovery_review = recovery_review_artifact.resolve()
    verify_complete_seal(
        raw, paired_calibration_root_sha256, label="paired calibration raw"
    )
    verify_complete_seal(
        recovery, recovery_root_sha256, label="paired calibration recovery"
    )
    verify_complete_seal(
        recovery_review,
        recovery_review_root_sha256,
        label="paired calibration recovery review",
    )
    if (
        (raw / "run.exit").read_bytes() != b"1\n"
        or (recovery / "run.exit").read_bytes() != b"0\n"
        or (recovery_review / "run.exit").read_bytes() != b"0\n"
    ):
        raise ValueError("accepted paired calibration run.exit chain drifted")
    recovery_report = _canonical_json(recovery / "report.json")
    review_report = _canonical_json(recovery_review / "report.json")
    if (
        recovery_report.get("status")
        != "recovered_calibration_analysis_complete_fresh_closed"
        or recovery_report.get("original_execution_root_sha256")
        != paired_calibration_root_sha256
        or recovery_report.get("terminal_arm_run_count") != 300
        or recovery_report.get("complete_arm_run_count") != 300
        or recovery_report.get("paired_eligible_pair_count") != 100
        or recovery_report.get("fresh_b2_opened") is not False
        or recovery_report.get("fresh_outcome_fields_consumed") != []
        or review_report.get("status")
        != "passed_independent_paired_calibration_recovery_review"
        or review_report.get("reviewed_recovery_root_sha256")
        != recovery_root_sha256
        or review_report.get("original_execution_root_sha256")
        != paired_calibration_root_sha256
        or review_report.get("terminal_arm_run_count") != 300
        or review_report.get("complete_arm_run_count") != 300
        or review_report.get("fresh_b2_opened") is not False
        or review_report.get("fresh_outcome_fields_consumed") != []
    ):
        raise ValueError("accepted paired calibration recovery authority drifted")
    roots = dict(recovery_report["input_roots"])
    paired_review._verify_input_roots(roots)
    base = validate_signal_complete_execution_plan(
        _canonical_json(Path(roots["plan_artifact"]) / "execution_plan.json")
    )
    paired = validate_paired_calibration_execution_plan(
        _canonical_json(
            Path(roots["paired_plan_artifact"])
            / "paired_calibration_plan.json"
        ),
        calibration_plan=base,
    )
    preregistration = validate_paired_calibration_preregistration(
        _canonical_json(
            Path(roots["preregistration_artifact"]) / "preregistration.json"
        )
    )
    paired_review._verify_preregistered_root_chain(preregistration, roots)
    return raw, recovery, recovery_review, roots, base, paired, preregistration


def _stream_candidate0_terminals(
    raw: Path, paired_plan: Mapping[str, Any]
) -> tuple[Iterator[dict[str, Any]], list[dict[str, Any]]]:
    receipt_rows: list[dict[str, Any]] = []

    def stream() -> Iterator[dict[str, Any]]:
        for unit in paired_plan["execution_units"]:
            order = unit["ordered_arms"].index(
                "candidate0_operational_default"
            )
            ordinal = unit["unit_ordinal"] * 3 + order
            relative = (
                f"runs/{ordinal:04d}_{unit['unit_ordinal']:04d}_{order}_"
                "candidate0_operational_default/terminal.json"
            )
            value, digest, size = _bounded_canonical_json(raw / relative)
            receipt_rows.append(
                {
                    "run_ordinal": ordinal,
                    "unit_ordinal": unit["unit_ordinal"],
                    "relative_path": relative,
                    "size_bytes": size,
                    "sha256": digest,
                }
            )
            yield _minimal_candidate0_terminal(value)

    return stream(), receipt_rows


def _minimal_candidate0_terminal(value: Mapping[str, Any]) -> dict[str, Any]:
    terminal = {
        name: value.get(name)
        for name in (
            "run_ordinal",
            "unit_ordinal",
            "unit_sha256",
            "arm_order_index",
            "plan_arm",
            "scenario_identity_sha256",
            "route_identity_sha256",
            "seed",
            "status",
            "fresh_b2_opened",
            "fresh_outcome_fields_consumed",
        )
    }
    if value.get("status") == "complete":
        native = value.get("native_receipt")
        if type(native) is not dict or type(native.get("ticks")) is not list:
            raise ValueError("paired candidate0 native receipt is missing")
        terminal["native_receipt"] = {
            name: native.get(name)
            for name in (
                "schema_version",
                "status",
                "arm",
                "fixed_dp_head",
                "claim_authorized",
                "route_name",
                "route_sha256",
                "spawn_config_sha256",
                "initial_state_sha256",
                "initial_input_sha256",
                "scenario_seed",
                "secondary",
            )
        }
        terminal["native_receipt"]["ticks"] = [
            {
                "tick_index": tick.get("tick_index"),
                "selected_index": tick.get("selected_index"),
                "candidate_tensor_sha256_before": tick.get(
                    "candidate_tensor_sha256_before"
                ),
                "candidate_tensor_sha256_after": tick.get(
                    "candidate_tensor_sha256_after"
                ),
                "input_sha256": tick.get("input_sha256"),
                "default_output_sha256": tick.get("default_output_sha256"),
                "pre_decision_speed_mps": tick.get(
                    "pre_decision_speed_mps"
                ),
                "safety": {
                    "speed_mps": (
                        tick.get("safety", {}).get("speed_mps")
                        if type(tick.get("safety")) is dict
                        else None
                    ),
                },
            }
            for tick in native["ticks"]
            if type(tick) is dict
        ]
        terminal["failure_receipt"] = None
    else:
        failure = value.get("failure_receipt")
        terminal["native_receipt"] = None
        terminal["failure_receipt"] = (
            {
                name: failure.get(name)
                for name in (
                    "failure_class",
                    "reason",
                    "raw_failure_receipt_sha256",
                )
            }
            if type(failure) is dict
            else failure
        )
    return terminal


def _calibration_root_bindings(
    *,
    preregistration: Mapping[str, Any],
    paired_calibration_root_sha256: str,
    recovery_review_root_sha256: str,
    preregistration_root_sha256: str,
) -> dict[str, str]:
    bindings = preregistration["root_artifacts"]
    return {
        "atom_audit_root": bindings["atom_audit"]["root_sha256"],
        "atom_audit_review_root": bindings["atom_audit_review"][
            "root_sha256"
        ],
        "training_root": bindings["training"]["root_sha256"],
        "training_review_root": bindings["training_review"]["root_sha256"],
        "calibration_corpus_root": paired_calibration_root_sha256,
        "calibration_review_root": recovery_review_root_sha256,
        "zero_overlap_root": preregistration_root_sha256,
    }


def _bounded_canonical_json(path: Path) -> tuple[dict[str, Any], str, int]:
    size = path.stat().st_size
    if size < 1 or size > MAX_TERMINAL_FILE_BYTES:
        raise ValueError(
            f"paired candidate0 terminal exceeds memory ceiling: {path}"
        )
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"))
    if type(value) is not dict or raw != _canonical_bytes(value):
        raise ValueError(
            f"paired candidate0 terminal is not canonical: {path}"
        )
    return value, hashlib.sha256(raw).hexdigest(), size


def _canonical_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"))
    if type(value) is not dict or raw != _canonical_bytes(value):
        raise ValueError(f"calibration authority JSON is not canonical: {path}")
    return value


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


def _heads_camp(path: Path) -> str:
    lines = path.read_text(encoding="ascii").splitlines()
    expected = [
        line.removeprefix("camp_head=")
        for line in lines
        if line.startswith("camp_head=")
    ]
    if len(expected) != 1:
        raise ValueError("calibration freeze HEADS drifted")
    return expected[0]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(
            _strict_equal(left[key], right[key]) for key in left
        )
    if type(left) is list:
        return len(left) == len(right) and all(
            _strict_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return bool(left == right)


def _write_json(path: Path, value: Any) -> None:
    path.write_bytes(_canonical_bytes(value))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = review(args.artifact, args.root_sha256)
    output = args.output_dir.resolve()
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    _write_json(output / "report.json", report)
    (output / "COMMAND").write_text(" ".join(sys.argv) + "\n", encoding="utf-8")
    (output / "run.exit").write_text("0\n", encoding="ascii")
    root = seal_artifact(
        output, label="V25 calibration freeze-from-paired independent review"
    )
    print(json.dumps({"status": report["status"], "root_sha256": root}, sort_keys=True))


if __name__ == "__main__":
    main()
