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
    CONTEXT_SCHEMA_VERSION,
    CORRECTED_GENERATION_SCALES,
    CORPUS_STEPS,
    EXPECTED_SEED,
    EXPECTED_TEMPLATE_SHA256,
    FORMAL_ARTIFACT,
    FORMAL_ROOT_SHA256,
    SUPERSEDED_PARTIAL_CORPUS_ROOT,
    _canonical_sha256,
    _file_sha256,
    _git_head,
    _tracked_dirty,
)
from scripts.integrations.preflight_diffusion_planner_v25_ultra_correction import (  # noqa: E402
    FINGERPRINT_PAYLOAD_KEYS,
    REQUIRED_PROBE_CHECKS,
    REQUIRED_REPORT_CHECKS,
    SCHEMA_VERSION as SOURCE_SCHEMA_VERSION,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    FIXED_DP_HEAD,
)


SCHEMA_VERSION = "camp_dp_v25_ultra_correction_preflight_review_v2"
IDENTITY_RECEIPT_KEYS = frozenset(
    {
        "elementwise_equal",
        "max_abs_difference",
        "default_output_sha256",
        "candidate0_sha256",
        "native_ranked_k8",
    }
)
AUTHORITY_KEYS = frozenset(
    {
        "schema_version",
        "camp_head",
        "released_camp_source_head",
        "current_repo_head_at_run",
        "fixed_dp_head",
        "formal_artifact",
        "formal_root_sha256",
        "probe_template",
        "probe_template_sha256",
        "generation_scales",
        "static_weights",
        "config_receipts_root_sha256",
        "seed",
        "corpus_steps_per_probe",
        "context_schema_version",
        "rejected_roots",
        "fresh_b_opened",
        "outcome_fields_consumed",
        "selector_runtime_mode",
        "scene14d_runtime_connected",
    }
)


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
    source_receipt = _load_json(artifact / "source_receipt.json")
    run_exit = (artifact / "run.exit").read_text(encoding="ascii")
    heads = _parse_heads((artifact / "HEADS").read_text(encoding="ascii"))
    command = (artifact / "COMMAND").read_text(encoding="utf-8").strip()
    rows = probes.get("probe_results")
    if not isinstance(rows, list) or not rows:
        raise ValueError("preflight probe results are missing")
    current_head = _git_head(ROOT)
    if _tracked_dirty(ROOT):
        raise ValueError("review current repo has tracked modifications")

    _require_keys("source report", report, AUTHORITY_KEYS | {"status", "mode", "checks"})
    _require_keys("source receipt", source_receipt, AUTHORITY_KEYS | {"config_receipts"})
    _require_exact_true_checks(
        "source report checks",
        report.get("checks"),
        REQUIRED_REPORT_CHECKS,
    )
    if probes.get("schema_version") != SOURCE_SCHEMA_VERSION:
        raise ValueError("probe-results schema version drifted")

    authority_equal = all(
        source_receipt.get(key) == report.get(key) for key in AUTHORITY_KEYS
    )
    config_receipts = source_receipt.get("config_receipts")
    config_checks = _review_config_receipts(
        config_receipts,
        expected_root=report.get("config_receipts_root_sha256"),
    )
    row_checks = [_review_probe_row(row, config_receipts) for row in rows]
    checks = {
        "source_schema": report.get("schema_version") == SOURCE_SCHEMA_VERSION,
        "source_status_passed": report.get("status") == "passed",
        "source_mode_bounded": report.get("mode")
        == "execute_bounded_correction_preflight",
        "source_run_exit_zero": run_exit == "0\n",
        "source_and_receipt_authority_equal": authority_equal,
        "released_head_is_current_repo_head": (
            report.get("camp_head")
            == report.get("released_camp_source_head")
            == report.get("current_repo_head_at_run")
            == current_head
        ),
        "heads_file_exact": heads
        == {
            "camp_source_head": current_head,
            "fixed_dp_head": FIXED_DP_HEAD,
        },
        "fixed_dp_bound": report.get("fixed_dp_head") == FIXED_DP_HEAD,
        "formal_authority_bound": (
            report.get("formal_artifact") == str(FORMAL_ARTIFACT)
            and report.get("formal_root_sha256") == FORMAL_ROOT_SHA256
            and _verify_seal(FORMAL_ARTIFACT) == FORMAL_ROOT_SHA256
        ),
        "template_authority_bound": (
            report.get("probe_template_sha256") == EXPECTED_TEMPLATE_SHA256
            and _file_sha256(Path(str(report.get("probe_template"))))
            == EXPECTED_TEMPLATE_SHA256
        ),
        "scale_authority_bound": (
            report.get("generation_scales", {}).get("path")
            == str(CORRECTED_GENERATION_SCALES)
            and _file_sha256(CORRECTED_GENERATION_SCALES)
            == report.get("generation_scales", {}).get("sha256")
        ),
        "static_weights_bound": _asset_receipt_is_live(report.get("static_weights")),
        "config_receipts_recomputed": all(config_checks.values()),
        "command_present": bool(command),
        "source_fresh_false": report.get("fresh_b_opened") is False,
        "source_outcomes_not_consumed": report.get("outcome_fields_consumed") == [],
        "source_full_corpus_not_started": report.get("full_corpus_started") is False,
        "source_training_calibration_not_executed": (
            report.get("training_executed") is False
            and report.get("calibration_executed") is False
        ),
        "source_sequential_k8": report.get("sequential_k8") is True,
        "no_optimization_mixed": (
            report.get("micro_batch_used") is False
            and report.get("cache_optimization_used") is False
            and report.get("snapshot_sharding_used") is False
        ),
        "old_partial_rejected": report.get("rejected_roots")
        == [SUPERSEDED_PARTIAL_CORPUS_ROOT],
        "three_probe_denominator": len(rows) == 3,
        "all_probe_ticks_64": all(
            row.get("tick_count") == CORPUS_STEPS for row in rows
        ),
        "all_probe_rows_recomputed": all(all(item.values()) for item in row_checks),
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
        "seed_and_context_bound": (
            report.get("seed") == EXPECTED_SEED
            and report.get("corpus_steps_per_probe") == CORPUS_STEPS
            and report.get("context_schema_version") == CONTEXT_SCHEMA_VERSION
        ),
        "static14d_only_scene_disconnected": (
            report.get("selector_runtime_mode") == "Static14D"
            and report.get("scene14d_runtime_connected") is False
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
        "config_checks": config_checks,
        "probe_row_checks": row_checks,
        "probe_count": len(rows),
        "probe_tick_count": sum(int(row["tick_count"]) for row in rows),
        "rejected_roots": [SUPERSEDED_PARTIAL_CORPUS_ROOT],
        "fresh_b_opened": False,
        "outcome_fields_consumed": [],
        "review_is_read_only": True,
    }


def _require_keys(name: str, payload: Any, required: frozenset[str]) -> None:
    if not isinstance(payload, dict):
        raise ValueError(f"{name} must be an object")
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError(f"{name} missing required keys: {','.join(missing)}")


def _require_exact_true_checks(
    name: str,
    payload: Any,
    required: frozenset[str],
) -> None:
    if not isinstance(payload, dict) or not payload:
        raise ValueError(f"{name} must be a nonempty object")
    if set(payload) != required:
        raise ValueError(f"{name} has missing or unexpected keys")
    if any(value is not True for value in payload.values()):
        raise ValueError(f"{name} contains a non-passing value")


def _parse_heads(text: str) -> dict[str, str]:
    rows = text.splitlines()
    if len(rows) != 2 or any(row.count("=") != 1 for row in rows):
        raise ValueError("HEADS must contain exactly two key/value lines")
    parsed = dict(row.split("=", 1) for row in rows)
    if set(parsed) != {"camp_source_head", "fixed_dp_head"}:
        raise ValueError("HEADS keys drifted")
    return parsed


def _asset_receipt_is_live(payload: Any) -> bool:
    if not isinstance(payload, dict) or set(payload) != {"path", "sha256"}:
        return False
    path = Path(str(payload["path"]))
    return path.is_file() and _file_sha256(path) == payload["sha256"]


def _review_config_receipts(
    receipts: Any,
    *,
    expected_root: Any,
) -> dict[str, bool]:
    if not isinstance(receipts, list) or len(receipts) != 2:
        raise ValueError("source receipt must bind exactly two unique probe configs")
    for receipt in receipts:
        _require_keys(
            "config receipt",
            receipt,
            frozenset(
                {
                    "scenario_id",
                    "family",
                    "route_identity_sha256",
                    "seed",
                    "config",
                    "config_sha256",
                }
            ),
        )
    recomputed = all(
        receipt["config_sha256"] == _canonical_sha256(receipt["config"])
        for receipt in receipts
    )
    root_matches = expected_root == _canonical_sha256(receipts)
    authorities = True
    for receipt in receipts:
        config = receipt["config"]
        protocol = config.get("protocol", {})
        selector = config.get("selector", {})
        scales = selector.get("atom_scales")
        weights = selector.get("weights")
        authorities &= (
            receipt.get("seed") == EXPECTED_SEED
            and config.get("fixed_dp", {}).get("head") == FIXED_DP_HEAD
            and isinstance(scales, dict)
            and scales.get("path") == str(CORRECTED_GENERATION_SCALES)
            and _asset_receipt_is_live(scales)
            and _asset_receipt_is_live(weights)
            and config.get("seeds", {}).get("scenario") == EXPECTED_SEED
            and protocol.get("corpus_steps") == CORPUS_STEPS
            and protocol.get("selector_training_execution_authorized") is False
            and protocol.get("calibration_authorized") is False
            and protocol.get("fresh_b_opened") is False
            and protocol.get("holdout_access_authorized") is False
            and config.get("controlled_scenario", {}).get("split") == "train"
            and config.get("controlled_scenario", {}).get("outcome_fields_consumed")
            == []
        )
    return {
        "config_receipt_hashes_recomputed": bool(recomputed),
        "config_receipt_root_recomputed": bool(root_matches),
        "config_authorities_bound": bool(authorities),
    }


def _review_probe_row(
    row: Any,
    config_receipts: list[dict[str, Any]],
) -> dict[str, bool]:
    _require_keys(
        "probe row",
        row,
        frozenset(
            {
                "scenario_id",
                "config_sha256",
                "tick_count",
                "tick_fingerprints",
                "tick_fingerprint_root_sha256",
                "selected_sequence",
                "selected_sequence_sha256",
                "checks",
                "fresh_b_opened",
                "outcome_fields_consumed",
            }
        ),
    )
    _require_exact_true_probe_checks(row.get("checks"))
    fingerprints = row.get("tick_fingerprints")
    if not isinstance(fingerprints, list) or len(fingerprints) != CORPUS_STEPS:
        raise ValueError("probe row must contain exactly 64 fingerprints")
    selected = []
    fingerprints_ok = True
    candidate0_ok = True
    for tick_index, fingerprint in enumerate(fingerprints):
        if not isinstance(fingerprint, dict) or set(fingerprint) != (
            FINGERPRINT_PAYLOAD_KEYS | {"fingerprint_sha256"}
        ):
            raise ValueError("probe fingerprint has missing or unexpected keys")
        payload = dict(fingerprint)
        digest = payload.pop("fingerprint_sha256")
        fingerprints_ok &= (
            fingerprint.get("tick_index") == tick_index
            and digest == _canonical_sha256(payload)
        )
        rows = fingerprint.get("candidate_row_sha256")
        index = fingerprint.get("selected_index")
        identity = fingerprint.get("default_candidate0_identity")
        if not isinstance(rows, list) or len(rows) != 8:
            raise ValueError("fingerprint candidate rows are invalid")
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < 8:
            raise ValueError("fingerprint selected index is invalid")
        candidate0_ok &= (
            isinstance(identity, dict)
            and set(identity) == IDENTITY_RECEIPT_KEYS
            and identity.get("elementwise_equal") is True
            and identity.get("max_abs_difference") == 0.0
            and identity.get("native_ranked_k8") is False
            and fingerprint.get("default_output_sha256") == rows[0]
            and fingerprint.get("candidate0_sha256") == rows[0]
            and identity.get("default_output_sha256") == rows[0]
            and identity.get("candidate0_sha256") == rows[0]
            and fingerprint.get("candidate0_semantics")
            == "operational_default_alias_from_same_forward"
            and fingerprint.get("candidate0_independent_second_forward") is False
            and fingerprint.get("selected_trajectory_sha256") == rows[index]
        )
        selected.append(index)
    config_hashes = {
        receipt["scenario_id"]: receipt["config_sha256"]
        for receipt in config_receipts
    }
    return {
        "fingerprints_recomputed": bool(fingerprints_ok),
        "fingerprint_root_recomputed": row.get("tick_fingerprint_root_sha256")
        == _canonical_sha256(fingerprints),
        "selected_sequence_recomputed": row.get("selected_sequence") == selected,
        "selected_sequence_root_recomputed": row.get("selected_sequence_sha256")
        == _canonical_sha256(selected),
        "default_candidate0_evidence_recomputed": bool(candidate0_ok),
        "config_hash_bound": config_hashes.get(row.get("scenario_id"))
        == row.get("config_sha256"),
        "fresh_and_outcomes_absent": (
            row.get("fresh_b_opened") is False
            and row.get("outcome_fields_consumed") == []
        ),
    }


def _require_exact_true_probe_checks(payload: Any) -> None:
    if not isinstance(payload, dict) or not payload:
        raise ValueError("probe checks must be nonempty")
    if set(payload) != REQUIRED_PROBE_CHECKS:
        raise ValueError("probe checks have missing or unexpected keys")
    if any(
        value is not True and not (name == "failure_class" and value is None)
        for name, value in payload.items()
    ):
        raise ValueError("probe checks contain a non-passing value")


if __name__ == "__main__":
    main()
