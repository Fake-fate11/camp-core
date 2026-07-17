#!/usr/bin/env python3
"""Create the read-only V25 Stage-A0 strict-inventory/authority supplement."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for _path in (ROOT, PACKAGE_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from camp_core.integrations.diffusion_planner_artifact_seal import (  # noqa: E402
    seal_artifact,
    verify_complete_seal,
)
from scripts.integrations.run_diffusion_planner_dp_camp_v21_native import (  # noqa: E402
    FIXED_DP_HEAD,
)
from scripts.integrations.run_diffusion_planner_v25_controlled_scenario_phase import (  # noqa: E402
    FORMAL_FORBIDDEN_SEEDS,
)
from scripts.integrations.run_diffusion_planner_v25_controlled_training_corpus import (  # noqa: E402
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


SCHEMA_VERSION = "camp_dp_v25_stage_a0_authority_supplement_v1"
S01_SOURCE_HEAD = "e6ba79a229ea3cc8e3a69d776ea1913cff8e3279"
S01_RELEASE_BASELINE_HEAD = "000d4308ba1a815a93f40a39a2a699cddcd3f3e5"
FAILED_PREFLIGHT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_s01_correction_preflight_e6ba79a2_20260717T184132CST"
)
FAILED_PREFLIGHT_ROOT = (
    "c4b0143ac60cfe67f47e5617517d72e24c18ec9007d84021e34901ed3e0c873a"
)
PASSED_PREFLIGHT = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_s01_correction_preflight_retry_e6ba79a2_20260717T184256CST"
)
PASSED_PREFLIGHT_ROOT = (
    "bba8f0581efa688a4a85f193eed966f38501ac96de4883c493ab81caa1760451"
)
PASSED_REVIEW = Path(
    "/root/autodl-tmp/"
    "camp_dp_v25_s01_correction_preflight_review_e6ba79a2_20260717T184530CST"
)
PASSED_REVIEW_ROOT = (
    "facfe0a1f4458e52ea2235197e7a2949537a1021c0d6fa69d5cf0018732f392d"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _write_json(path: Path, payload: Any) -> None:
    Path(path).write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _expected_probe_cases(plan: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    train = plan.get("train")
    if not isinstance(train, list):
        raise ValueError("formal train plan is absent")
    executable = [case for case in train if case.get("runner_eligible") is True]
    if not executable or executable[0].get("family") != "lead_vehicle_hard_brake":
        raise ValueError("formal identity0 drifted")
    red_easy = next(
        (
            case
            for case in executable
            if case.get("family") == "red_light_phase_timing"
            and case.get("tier") == "easy"
        ),
        None,
    )
    if red_easy is None:
        raise ValueError("formal red-light/easy case is absent")
    return [executable[0], red_easy]


def validate_probe_config_authority(
    *,
    preflight_root: Path,
    formal_root: Path,
) -> dict[str, Any]:
    report = _load_json(preflight_root / "report.json")
    source = _load_json(preflight_root / "source_receipt.json")
    formal_report = _load_json(formal_root / "report.json")
    formal_source = _load_json(formal_root / "source_receipt.json")
    formal_plan = _load_json(formal_root / "controlled_corpus_final_plan.json")
    expected_cases = _expected_probe_cases(formal_plan)
    receipts = source.get("config_receipts")
    if not isinstance(receipts, list) or len(receipts) != 2:
        raise ValueError("preflight must bind exactly two probe configs")
    expected_ids = [str(case["scenario_id"]) for case in expected_cases]
    if [receipt.get("scenario_id") for receipt in receipts] != expected_ids:
        raise ValueError("probe configs are not the two ordered formal cases")
    if len(set(expected_ids)) != 2:
        raise ValueError("formal probe cases are not unique")
    if report.get("config_receipts_root_sha256") != _canonical_sha256(receipts):
        raise ValueError("probe config receipt root mismatch")
    if formal_report.get("status") != "passed" or formal_report.get("mode") != "freeze_formal":
        raise ValueError("formal source report is not the passed freeze")
    if (
        formal_source.get("camp_head") != S01_SOURCE_HEAD
        and formal_source.get("camp_head") != "ff028387c17600f65fb23b3d8047e562203e2881"
    ):
        raise ValueError("formal source CAMP authority is unexpected")
    if formal_source.get("fixed_dp_head") != FIXED_DP_HEAD:
        raise ValueError("formal fixed-DP authority drifted")
    if (
        formal_source.get("probe_template_sha256") != EXPECTED_TEMPLATE_SHA256
        or report.get("probe_template_sha256") != EXPECTED_TEMPLATE_SHA256
        or source.get("probe_template_sha256") != EXPECTED_TEMPLATE_SHA256
    ):
        raise ValueError("probe template authority drifted")
    expected_scale = {
        "path": str(CORRECTED_GENERATION_SCALES),
        "sha256": _file_sha256(CORRECTED_GENERATION_SCALES),
    }
    if report.get("generation_scales") != expected_scale or source.get(
        "generation_scales"
    ) != expected_scale:
        raise ValueError("generation-scale authority drifted")

    common_weights = report.get("static_weights")
    if not isinstance(common_weights, dict) or source.get("static_weights") != common_weights:
        raise ValueError("static-weight receipt drifted")
    weights_path = Path(str(common_weights.get("path")))
    if (
        set(common_weights) != {"path", "sha256"}
        or not weights_path.is_file()
        or _file_sha256(weights_path) != common_weights.get("sha256")
    ):
        raise ValueError("static-weight payload is not live")

    row_checks: list[dict[str, Any]] = []
    for receipt, case in zip(receipts, expected_cases, strict=True):
        config = receipt.get("config")
        if not isinstance(config, dict):
            raise ValueError("probe config payload is invalid")
        identity = str(case["route_identity_sha256"])
        route_rows = config.get("routes")
        if not isinstance(route_rows, list) or len(route_rows) != 1:
            raise ValueError("probe config must bind one explicit route")
        route = route_rows[0]
        route_path = Path(str(route.get("path")))
        exact = {
            "receipt_fields_equal": (
                receipt.get("family") == case.get("family")
                and receipt.get("route_identity_sha256") == identity
                and receipt.get("seed") == EXPECTED_SEED
            ),
            "formal_case_exact": config.get("controlled_scenario") == case,
            "map_exact": config.get("map")
            == {
                "path": str(case["source_map_path"]),
                "sha256": str(case["source_map_sha256"]),
            },
            "route_exact": (
                isinstance(route, dict)
                and route.get("name") == identity
                and route_path.is_file()
                and route.get("sha256") == _file_sha256(route_path)
            ),
            "seed_exact": config.get("seeds")
            == {
                "scenario": EXPECTED_SEED,
                "candidate": EXPECTED_SEED,
                "bootstrap": EXPECTED_SEED,
                "formal_forbidden": list(FORMAL_FORBIDDEN_SEEDS),
            },
            "fixed_dp_exact": config.get("fixed_dp", {}).get("head") == FIXED_DP_HEAD,
            "scale_exact": config.get("selector", {}).get("atom_scales")
            == expected_scale,
            "weights_exact": config.get("selector", {}).get("weights")
            == common_weights,
            "protocol_exact": (
                config.get("protocol", {}).get("corpus_steps") == CORPUS_STEPS
                and config.get("protocol", {}).get("candidate_k") == 8
                and config.get("protocol", {}).get("fresh_b_opened") is False
                and config.get("protocol", {}).get("calibration_authorized") is False
                and config.get("protocol", {}).get(
                    "selector_training_execution_authorized"
                )
                is False
            ),
            "config_hash_recomputed": receipt.get("config_sha256")
            == _canonical_sha256(config),
        }
        if not all(exact.values()):
            failed = [name for name, passed in exact.items() if not passed]
            raise ValueError("probe config authority failed: " + ",".join(failed))
        row_checks.append(
            {
                "scenario_id": case["scenario_id"],
                "family": case["family"],
                "tier": case["tier"],
                "route_identity_sha256": identity,
                "checks": exact,
            }
        )
    return {
        "formal_case_count": len(expected_cases),
        "formal_case_ids": expected_ids,
        "config_receipts_root_sha256": _canonical_sha256(receipts),
        "shared_template_sha256": EXPECTED_TEMPLATE_SHA256,
        "shared_generation_scales": expected_scale,
        "shared_static_weights": common_weights,
        "rows": row_checks,
    }


def build_report() -> dict[str, Any]:
    current_head = _git_head(ROOT)
    if _tracked_dirty(ROOT):
        raise ValueError("current CAMP tracked worktree is dirty")
    roots = {
        "failed_preflight": (FAILED_PREFLIGHT, FAILED_PREFLIGHT_ROOT),
        "passed_preflight": (PASSED_PREFLIGHT, PASSED_PREFLIGHT_ROOT),
        "passed_review": (PASSED_REVIEW, PASSED_REVIEW_ROOT),
        "formal_source": (FORMAL_ARTIFACT, FORMAL_ROOT_SHA256),
    }
    inventory = {
        name: verify_complete_seal(path, digest, label=name)
        for name, (path, digest) in roots.items()
    }
    if (FAILED_PREFLIGHT / "run.exit").read_text(encoding="ascii") != "1\n":
        raise ValueError("failed preflight diagnostic run.exit drifted")
    if (PASSED_PREFLIGHT / "run.exit").read_text(encoding="ascii") != "0\n":
        raise ValueError("passed preflight run.exit drifted")
    if (PASSED_REVIEW / "run.exit").read_text(encoding="ascii") != "0\n":
        raise ValueError("passed review run.exit drifted")
    review = _load_json(PASSED_REVIEW / "report.json")
    if (
        review.get("status") != "passed"
        or review.get("reviewed_root_sha256") != PASSED_PREFLIGHT_ROOT
        or not isinstance(review.get("checks"), dict)
        or not review["checks"]
        or any(value is not True for value in review["checks"].values())
    ):
        raise ValueError("S0.1 review authority drifted")
    probe = validate_probe_config_authority(
        preflight_root=PASSED_PREFLIGHT,
        formal_root=FORMAL_ARTIFACT,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed",
        "stage": "A0_authority_hardening",
        "stage_a0_code_head": current_head,
        "released_s01_source_head": S01_SOURCE_HEAD,
        "released_s01_final_baseline_head": S01_RELEASE_BASELINE_HEAD,
        "fixed_dp_head": FIXED_DP_HEAD,
        "strict_inventory": inventory,
        "probe_authority": probe,
        "rejected_roots": [SUPERSEDED_PARTIAL_CORPUS_ROOT],
        "failed_preflight_role": "diagnostic_only_training_calibration_evaluation_ineligible",
        "existing_3x64_model_rerun": False,
        "gpu_work_started": False,
        "stage_a_authorized": True,
        "r_authorized": False,
        "training_authorized": False,
        "calibration_authorized": False,
        "scene_runtime_authorized": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def main() -> None:
    args = parse_args()
    if args.output_dir.exists():
        raise FileExistsError(f"output already exists: {args.output_dir}")
    args.output_dir.mkdir(parents=True)
    try:
        report = build_report()
        _write_json(args.output_dir / "report.json", report)
        (args.output_dir / "HEADS").write_text(
            f"camp_head={report['stage_a0_code_head']}\n"
            f"fixed_dp_head={FIXED_DP_HEAD}\n",
            encoding="ascii",
        )
        (args.output_dir / "COMMAND").write_text(
            " ".join(sys.argv) + "\n", encoding="utf-8"
        )
        (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
        root_sha256 = seal_artifact(args.output_dir, label="V25 Stage A0 supplement")
        print(
            json.dumps(
                {
                    "status": "passed",
                    "root_sha256": root_sha256,
                    "output_dir": str(args.output_dir),
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
                "fresh_b2_opened": False,
                "outcome_fields_consumed": [],
            },
        )
        (args.output_dir / "run.exit").write_text("1\n", encoding="ascii")
        seal_artifact(args.output_dir, label="V25 Stage A0 failed supplement")
        raise


if __name__ == "__main__":
    main()
