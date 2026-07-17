#!/usr/bin/env python3
"""Independently rebuild and review the sealed V25 1500-config preflight."""

from __future__ import annotations

import argparse
import collections
import hashlib
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
from camp_core.integrations.diffusion_planner_v25_full_r_authority import (  # noqa: E402
    FIXED_DP_HEAD,
    PREFLIGHT_RELEASE_SCHEMA_VERSION,
    canonical_sha256,
    file_sha256,
    verify_dual_head_contract,
    verify_seven_root_chain,
)
from camp_core.integrations.diffusion_planner_v25_semantic_authority import (  # noqa: E402
    validate_no_signal_chain,
    validate_signal_chain,
)


SCHEMA_VERSION = "camp_dp_v25_full_config_preflight_review_v2"
EXECUTION_SCHEMA_VERSION = "camp_dp_v25_controlled_training_corpus_execution_v3"
EXPECTED_EXECUTABLE_IDENTITIES = 1500
EXPECTED_RETAINED_INELIGIBLE = 153
EXPECTED_SEED = 25001
CORPUS_STEPS = 64
CONTEXT_SCHEMA_VERSION = "camp_dp_v25_causal_context_raw_v2"
SUPERSEDED_PARTIAL_CORPUS_ROOT = (
    "a2f69cdc352528c599b76904dd42df882c162fe610775ac7d8164b7ddb4c2481"
)
CONFIG_RECEIPT_FIELDS = {
    "schema_version",
    "scenario_id",
    "family",
    "tier",
    "route_identity_sha256",
    "canonical_semantic_clone_sha256",
    "signal_source_chain_sha256",
    "map_sha256",
    "route_sha256",
    "fixed_dp_head",
    "fixed_dp_checkpoint_sha256",
    "fixed_dp_args_sha256",
    "generation_scales_sha256",
    "static_weights_sha256",
    "selector_role",
    "seed",
    "corpus_steps",
    "context_schema_version",
    "context_mode",
    "selector_training_execution_authorized",
    "calibration_authorized",
    "holdout_access_authorized",
    "fresh_b_opened",
    "outcome_fields_consumed",
    "config_authority_sha256",
}
REQUIRED_REPORT_FIELDS = {
    "schema_version",
    "status",
    "mode",
    "camp_head",
    "implementation_source_head",
    "released_camp_source_head",
    "current_repo_head_at_run",
    "fixed_dp_head",
    "formal_artifact",
    "formal_root_sha256",
    "probe_template",
    "probe_template_sha256",
    "generation_scales",
    "static_weights",
    "seed",
    "corpus_steps",
    "snapshot_capacity",
    "train_lock",
    "minimum_free_bytes",
    "rejected_roots",
    "r0_review_artifact",
    "r0_review_root_sha256",
    "r0_source_artifact",
    "r0_source_root_sha256",
    "seven_root_bindings",
    "seven_root_bindings_sha256",
    "release_run_nonce",
    "authorized_output_dir",
    "critical_implementation_manifest",
    "ultra_full_config_preflight_release_artifact",
    "ultra_full_config_preflight_release_root_sha256",
    "semantic_authority_root_sha256",
    "semantic_authority_identity_count",
    "semantic_authority_chains_root_sha256",
    "terminal_lock_scope",
    "free_bytes_at_start",
    "fresh_b_opened",
    "outcome_fields_consumed",
    "config_receipts_root_sha256",
    "validated_identity_count",
    "source_ineligible_retained_identity_count",
    "retained_ineligible_receipts",
    "retained_ineligible_receipts_root_sha256",
    "formal_train_manifest_identity_count",
    "unique_route_count",
    "family_counts",
    "tier_counts",
    "model_loaded",
    "candidate_generation_started",
    "simulator_started",
    "training_executed",
    "calibration_executed",
    "claim_authorized",
    "config_receipts",
}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _verify_asset(payload: Any) -> dict[str, str]:
    if not isinstance(payload, Mapping) or set(payload) != {"path", "sha256"}:
        raise ValueError("asset receipt field set drifted")
    path = Path(str(payload["path"]))
    if not path.is_file() or path.is_symlink() or file_sha256(path) != payload["sha256"]:
        raise ValueError(f"asset receipt does not match the actual file: {path}")
    return {"path": str(path), "sha256": str(payload["sha256"])}


def _retained_ineligible_receipts(plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    result = []
    for case in plan["train"]:
        if case.get("runner_eligible") is not False:
            continue
        result.append(
            {
                "scenario_id": str(case["scenario_id"]),
                "family": str(case["family"]),
                "tier": str(case["tier"]),
                "route_identity_sha256": str(case["route_identity_sha256"]),
                "source_map_sha256": str(case["source_map_sha256"]),
                "source_requirements": list(case["source_requirements"]),
                "source_availability": dict(case["source_availability"]),
                "retention_role": str(case["retention_role"]),
            }
        )
    return result


def _independent_config_receipts(
    *,
    preflight: Path,
    cases: list[Mapping[str, Any]],
    chains: list[Mapping[str, Any]],
    template: Mapping[str, Any],
    generation_scales_sha256: str,
    static_weights_sha256: str,
) -> list[dict[str, Any]]:
    chain_by_id: dict[str, dict[str, Any]] = {}
    for raw_chain in chains:
        if raw_chain.get("expected_current_phase") is None:
            chain = validate_no_signal_chain(raw_chain)
        else:
            chain = validate_signal_chain(raw_chain)
        scenario_id = str(chain["scenario_id"])
        if scenario_id in chain_by_id:
            raise ValueError("semantic authority contains duplicate identities")
        chain_by_id[scenario_id] = chain
    if len(chain_by_id) != len(cases):
        raise ValueError("semantic authority identity denominator drifted")

    fixed_dp = template.get("fixed_dp")
    if not isinstance(fixed_dp, Mapping) or fixed_dp.get("head") != FIXED_DP_HEAD:
        raise ValueError("fixed-DP template authority drifted")
    checkpoint = _verify_asset(fixed_dp.get("checkpoint"))
    args_json = _verify_asset(fixed_dp.get("args_json"))
    receipts = []
    for case in cases:
        scenario_id = str(case["scenario_id"])
        chain = chain_by_id.get(scenario_id)
        if chain is None:
            raise ValueError("formal identity has no independently valid source chain")
        identity = str(case["route_identity_sha256"])
        if (
            chain.get("route_identity_sha256") != identity
            or chain.get("source_map_sha256") != case.get("source_map_sha256")
            or chain.get("semantic_clone_payload", {}).get("family")
            != case.get("family")
            or chain.get("semantic_clone_payload", {}).get("tier")
            != case.get("tier")
        ):
            raise ValueError("source chain does not match the formal semantic identity")
        map_path = Path(str(case["source_map_path"]))
        route_path = preflight / "routes" / f"{identity}.pkl"
        if (
            not map_path.is_file()
            or map_path.is_symlink()
            or file_sha256(map_path) != case["source_map_sha256"]
            or not route_path.is_file()
            or route_path.is_symlink()
        ):
            raise ValueError("formal map/route actual SHA authority drifted")
        authority = {
            "schema_version": "camp_dp_v25_controlled_train_v2",
            "scenario_id": scenario_id,
            "family": str(case["family"]),
            "tier": str(case["tier"]),
            "route_identity_sha256": identity,
            "canonical_semantic_clone_sha256": str(
                chain["semantic_clone_sha256"]
            ),
            "signal_source_chain_sha256": str(chain["source_chain_sha256"]),
            "map_sha256": file_sha256(map_path),
            "route_sha256": file_sha256(route_path),
            "fixed_dp_head": FIXED_DP_HEAD,
            "fixed_dp_checkpoint_sha256": checkpoint["sha256"],
            "fixed_dp_args_sha256": args_json["sha256"],
            "generation_scales_sha256": generation_scales_sha256,
            "static_weights_sha256": static_weights_sha256,
            "selector_role": "v25_controlled_train_fixed_static_behavior_policy",
            "seed": EXPECTED_SEED,
            "corpus_steps": CORPUS_STEPS,
            "context_schema_version": CONTEXT_SCHEMA_VERSION,
            "context_mode": "no_v2i",
            "selector_training_execution_authorized": False,
            "calibration_authorized": False,
            "holdout_access_authorized": False,
            "fresh_b_opened": False,
            "outcome_fields_consumed": [],
        }
        receipts.append(
            {**authority, "config_authority_sha256": canonical_sha256(authority)}
        )
    return receipts


def review(preflight: Path, expected_root: str) -> dict[str, Any]:
    seal = verify_complete_seal(
        preflight, expected_root, label="V25 full-config preflight"
    )
    report = _load(preflight / "report.json")
    source = _load(preflight / "source_receipt.json")
    if (
        (preflight / "run.exit").read_text(encoding="ascii") != "0\n"
        or source != report
        or set(report) != REQUIRED_REPORT_FIELDS
        or report.get("schema_version") != EXECUTION_SCHEMA_VERSION
        or report.get("status") != "passed"
        or report.get("mode") != "preflight"
        or report.get("fixed_dp_head") != FIXED_DP_HEAD
        or report.get("implementation_source_head")
        != report.get("released_camp_source_head")
        or report.get("camp_head") != report.get("current_repo_head_at_run")
        or report.get("rejected_roots") != [SUPERSEDED_PARTIAL_CORPUS_ROOT]
        or report.get("corpus_steps") != CORPUS_STEPS
        or report.get("validated_identity_count")
        != EXPECTED_EXECUTABLE_IDENTITIES
        or report.get("source_ineligible_retained_identity_count")
        != EXPECTED_RETAINED_INELIGIBLE
        or report.get("formal_train_manifest_identity_count")
        != EXPECTED_EXECUTABLE_IDENTITIES + EXPECTED_RETAINED_INELIGIBLE
        or report.get("snapshot_capacity")
        != EXPECTED_EXECUTABLE_IDENTITIES * CORPUS_STEPS
        or report.get("semantic_authority_identity_count")
        != EXPECTED_EXECUTABLE_IDENTITIES
        or report.get("model_loaded") is not False
        or report.get("candidate_generation_started") is not False
        or report.get("simulator_started") is not False
        or report.get("training_executed") is not False
        or report.get("calibration_executed") is not False
        or report.get("fresh_b_opened") is not False
        or report.get("claim_authorized") is not False
        or report.get("outcome_fields_consumed") != []
    ):
        raise ValueError("full-config preflight report contract drifted")
    heads = (preflight / "HEADS").read_text(encoding="ascii").splitlines()
    if heads != [
        f"camp_source_head={report['implementation_source_head']}",
        f"camp_pointer_head={report['camp_head']}",
        f"fixed_dp_head={FIXED_DP_HEAD}",
    ] or not (preflight / "COMMAND").read_text(encoding="utf-8").strip():
        raise ValueError("full-config preflight HEADS/COMMAND drifted")
    verify_dual_head_contract(
        repo=ROOT,
        implementation_source_head=str(report["implementation_source_head"]),
        current_pointer_head=str(report["camp_head"]),
        implementation_manifest=report["critical_implementation_manifest"],
    )
    verified_roots = verify_seven_root_chain(
        bindings=report["seven_root_bindings"],
        implementation_source_head=str(report["implementation_source_head"]),
        fixed_dp_head=FIXED_DP_HEAD,
        rejected_root_sha256=SUPERSEDED_PARTIAL_CORPUS_ROOT,
    )
    if (
        report.get("seven_root_bindings_sha256")
        != canonical_sha256(report["seven_root_bindings"])
        or report.get("r0_source_root_sha256")
        != verified_roots["r01_source"]["root_sha256"]
        or report.get("r0_review_root_sha256")
        != verified_roots["r01_bounded_review"]["root_sha256"]
    ):
        raise ValueError("full-config seven-root machine authority drifted")
    release_artifact = Path(
        str(report["ultra_full_config_preflight_release_artifact"])
    )
    verify_complete_seal(
        release_artifact,
        str(report["ultra_full_config_preflight_release_root_sha256"]),
        label="V25 full-config preflight release",
    )
    release = _load(release_artifact / "decision.json")
    if (
        (release_artifact / "run.exit").read_text(encoding="ascii") != "0\n"
        or release.get("schema_version") != PREFLIGHT_RELEASE_SCHEMA_VERSION
        or release.get("status") != "full_config_preflight_released"
        or release.get("implementation_source_head")
        != report["implementation_source_head"]
        or release.get("root_artifacts") != report["seven_root_bindings"]
        or release.get("rejected_roots") != report["rejected_roots"]
        or release.get("critical_implementation_manifest")
        != report["critical_implementation_manifest"]
        or release.get("run_nonce") != report["release_run_nonce"]
        or Path(str(release.get("authorized_output_dir"))).resolve()
        != preflight.resolve()
        or Path(str(report["authorized_output_dir"])).resolve()
        != preflight.resolve()
        or release.get("full_config_preflight_authorized") is not True
        or release.get("full_r_execute_authorized") is not False
        or release.get("fresh_b2_opened") is not False
        or release.get("outcome_fields_consumed") != []
    ):
        raise ValueError("full-config preflight release binding drifted")

    formal = Path(str(report["formal_artifact"]))
    verify_complete_seal(
        formal, str(report["formal_root_sha256"]), label="V25 formal plan"
    )
    formal_report = _load(formal / "report.json")
    plan = _load(formal / "controlled_corpus_final_plan.json")
    executable = [case for case in plan["train"] if case.get("runner_eligible") is True]
    ineligible = _retained_ineligible_receipts(plan)
    if (
        (formal / "run.exit").read_text(encoding="ascii") != "0\n"
        or formal_report.get("status") != "passed"
        or formal_report.get("mode") != "freeze_formal"
        or plan.get("outcome_blind") is not True
        or plan.get("outcome_fields_consumed") != []
        or plan.get("fresh_b_outcome_opened") is not False
        or len(executable) != EXPECTED_EXECUTABLE_IDENTITIES
        or len(ineligible) != EXPECTED_RETAINED_INELIGIBLE
        or any(case.get("seeds") != [EXPECTED_SEED] for case in executable)
        or any(case.get("split") != "train" for case in executable)
        or any(case.get("outcome_fields_consumed") != [] for case in executable)
        or any(case.get("holdout_outcome_consumed") is not False for case in executable)
        or report.get("retained_ineligible_receipts") != ineligible
        or report.get("retained_ineligible_receipts_root_sha256")
        != canonical_sha256(ineligible)
    ):
        raise ValueError("formal retained-ineligible denominator/root drifted")

    template_path = Path(str(report["probe_template"]))
    if file_sha256(template_path) != report["probe_template_sha256"]:
        raise ValueError("probe template actual SHA drifted")
    template = _load(template_path)
    scales = _verify_asset(report["generation_scales"])
    weights = _verify_asset(report["static_weights"])
    if template.get("selector", {}).get("weights") != weights:
        raise ValueError("template/static-weight authority drifted")
    chain_payload = _load(preflight / "semantic_authority_chains.json")
    chains = chain_payload.get("chains")
    if (
        set(chain_payload)
        != {"schema_version", "identity_count", "chains_root_sha256", "chains"}
        or chain_payload.get("identity_count") != EXPECTED_EXECUTABLE_IDENTITIES
        or not isinstance(chains, list)
        or len(chains) != EXPECTED_EXECUTABLE_IDENTITIES
        or chain_payload.get("chains_root_sha256") != canonical_sha256(chains)
        or report.get("semantic_authority_chains_root_sha256")
        != canonical_sha256(chains)
    ):
        raise ValueError("semantic authority chain sidecar drifted")
    semantic_receipts = [
        {
            "scenario_id": str(chain["scenario_id"]),
            "semantic_clone_sha256": str(chain["semantic_clone_sha256"]),
            "source_chain_sha256": str(chain["source_chain_sha256"]),
        }
        for chain in chains
    ]
    if report.get("semantic_authority_root_sha256") != canonical_sha256(
        semantic_receipts
    ):
        raise ValueError("semantic authority receipt root drifted")
    expected = _independent_config_receipts(
        preflight=preflight,
        cases=executable,
        chains=chains,
        template=template,
        generation_scales_sha256=scales["sha256"],
        static_weights_sha256=weights["sha256"],
    )
    receipts = report.get("config_receipts")
    if (
        not isinstance(receipts, list)
        or any(not isinstance(row, Mapping) or set(row) != CONFIG_RECEIPT_FIELDS for row in receipts)
        or receipts != expected
        or report.get("config_receipts_root_sha256") != canonical_sha256(expected)
        or report.get("family_counts")
        != dict(collections.Counter(case["family"] for case in executable))
        or report.get("tier_counts")
        != dict(collections.Counter(case["tier"] for case in executable))
        or report.get("unique_route_count")
        != len({case["route_identity_sha256"] for case in executable})
    ):
        raise ValueError("independently rebuilt full-config receipts/root drifted")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "passed_independent_1500_config_preflight_review_execute_closed",
        "implementation_source_head": report["implementation_source_head"],
        "review_pointer_head": report["camp_head"],
        "fixed_dp_head": FIXED_DP_HEAD,
        "reviewed_artifact": str(preflight),
        "reviewed_root_sha256": seal["root_sha256"],
        "identity_count": EXPECTED_EXECUTABLE_IDENTITIES,
        "executable_config_count": EXPECTED_EXECUTABLE_IDENTITIES,
        "retained_source_ineligible_count": EXPECTED_RETAINED_INELIGIBLE,
        "corpus_steps": CORPUS_STEPS,
        "snapshot_capacity": EXPECTED_EXECUTABLE_IDENTITIES * CORPUS_STEPS,
        "config_receipts_root_sha256": canonical_sha256(expected),
        "retained_ineligible_receipts_root_sha256": canonical_sha256(ineligible),
        "seven_root_bindings_sha256": report["seven_root_bindings_sha256"],
        "full_r_execute_authorized": False,
        "fresh_b2_opened": False,
        "outcome_fields_consumed": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-artifact", type=Path, required=True)
    parser.add_argument("--preflight-root-sha256", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    args.output_dir.mkdir(parents=True)
    try:
        report = review(args.preflight_artifact, args.preflight_root_sha256)
        _write(args.output_dir / "report.json", report)
        (args.output_dir / "HEADS").write_text(
            (
                f"camp_source_head={report['implementation_source_head']}\n"
                f"camp_pointer_head={report['review_pointer_head']}\n"
                f"fixed_dp_head={FIXED_DP_HEAD}\n"
            ),
            encoding="ascii",
        )
        (args.output_dir / "COMMAND").write_text(
            " ".join(sys.argv) + "\n", encoding="utf-8"
        )
        (args.output_dir / "run.exit").write_text("0\n", encoding="ascii")
        root = seal_artifact(args.output_dir, label="V25 full-config preflight review")
        print(json.dumps({"status": report["status"], "root_sha256": root}))
    except BaseException as exc:
        _write(
            args.output_dir / "failure.json",
            {"schema_version": SCHEMA_VERSION, "status": "failed", "reason": str(exc)},
        )
        (args.output_dir / "run.exit").write_text("1\n", encoding="ascii")
        seal_artifact(args.output_dir, label="V25 failed full-config preflight review")
        raise


if __name__ == "__main__":
    main()
