#!/usr/bin/env python3
"""Read-only v19 native-baseline and closed-loop evidence-gap audit."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
BASELINE_NAME = "DP-default deterministic/MAP baseline"
SOURCE_CONTRACTS = (
    (
        "diffusion_planner/diffusion_planner/model/module/decoder.py",
        'return {"prediction": x0',
        "single decoder prediction output",
    ),
    (
        "scenario_generation/tensor_converter.py",
        'data_torch["sampled_trajectories"] = torch.zeros',
        "deterministic zero initial latent",
    ),
    (
        "scenario_generation/simulate.py",
        'outputs["prediction"][0, 0]',
        "default replay consumes the single ego prediction",
    ),
    (
        "diffusion_planner_ros/diffusion_planner_ros/diffusion_planner_node.py",
        'declare_parameter("batch_size", value=1)',
        "ROS default batch size is one",
    ),
    (
        "diffusion_planner_ros/diffusion_planner_ros/diffusion_planner_node.py",
        "curr_pred = pred[b, 0]",
        "ROS trajectory source is the ego output for batch item b",
    ),
    (
        "diffusion_planner_ros/diffusion_planner_ros/diffusion_planner_node.py",
        "if b == 0:",
        "ROS compatibility output publishes batch item zero",
    ),
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _source_evidence(dp_repo: Path) -> tuple[list[dict[str, Any]], bool]:
    by_path: dict[str, dict[str, Any]] = {}
    all_passed = True
    for relative_path, token, contract in SOURCE_CONTRACTS:
        path = dp_repo / relative_path
        if not path.is_file():
            raise FileNotFoundError(f"missing fixed-DP provenance source: {path}")
        data = path.read_bytes()
        item = by_path.setdefault(
            relative_path,
            {
                "path": relative_path,
                "sha256": _sha256(data),
                "git_blob_sha1": _git_blob_sha1(data),
                "contracts": [],
            },
        )
        passed = token.encode("utf-8") in data
        item["contracts"].append(
            {"description": contract, "required_token": token, "passed": passed}
        )
        all_passed = all_passed and passed
    return list(by_path.values()), all_passed


def _nuplan_references(dp_repo: Path) -> tuple[list[str], bool]:
    references = []
    closed_loop_adapter = False
    for path in sorted(dp_repo.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.suffix.lower() not in {".py", ".md", ".yaml", ".yml", ".json"}:
            continue
        data = path.read_bytes().lower()
        if b"nuplan" not in data:
            continue
        references.append(path.relative_to(dp_repo).as_posix())
        if path.suffix.lower() == ".py" and b"simulation" in data and b"planner" in data:
            closed_loop_adapter = True
    return references, closed_loop_adapter


def build_report(
    *,
    camp_repo: Path,
    dp_repo: Path,
    nuplan_data_root: Path,
    camp_head: str,
    dp_head: str,
    nuplan_devkit_available: bool,
    official_nuplan_simulator_available: bool,
) -> dict[str, Any]:
    if dp_head != FIXED_DP_HEAD:
        raise ValueError(f"fixed DP HEAD drift: {dp_head}")
    source_files, contracts_passed = _source_evidence(dp_repo)
    nuplan_references, fixed_dp_nuplan_adapter = _nuplan_references(dp_repo)
    database_paths = sorted(nuplan_data_root.rglob("*.db"))
    database_bytes = sum(path.stat().st_size for path in database_paths)
    map_paths = sorted(nuplan_data_root.rglob("map.gpkg"))
    simulator_ready = bool(
        nuplan_devkit_available and official_nuplan_simulator_available
    )
    return {
        "schema_version": "dp_camp_v19_safety_evidence_gap_audit_v1",
        "heads": {
            "camp": camp_head,
            "fixed_dp": dp_head,
        },
        "claim_taxonomy": {
            "performance_claim": "no_claim",
            "bounded_offline_safety_proxy_improvement": "supported",
            "closed_loop_safety_claim": "not_yet_supported",
            "broad_CAMP_over_native_DP_Top1_claim": "not_supported",
        },
        "native_baseline_provenance": {
            "baseline_name": BASELINE_NAME,
            "candidate0_semantics": "fixed-DP deterministic/MAP candidate-0",
            "candidate0_is_native_top1": False,
            "native_ranked_top1": False,
            "native_ranking_path_found": False,
            "native_top1_goal_completed": False,
            "native_inference_source_contracts_passed": contracts_passed,
            "default_source_provenance_status": (
                "source_contract_established_execution_not_yet_paired"
                if contracts_passed
                else "source_contract_failed"
            ),
            "source_files": source_files,
        },
        "nuplan_capability": {
            "data_root": str(nuplan_data_root),
            "database_count": len(database_paths),
            "database_bytes": database_bytes,
            "map_database_count": len(map_paths),
            "nuplan_devkit_available": bool(nuplan_devkit_available),
            "official_nuplan_simulator_available": bool(
                official_nuplan_simulator_available
            ),
            "camp_causal_sqlite_adapter_present": (
                camp_repo
                / "camp_core"
                / "camp_core"
                / "integrations"
                / "nuplan_causal_adapter.py"
            ).is_file(),
            "fixed_dp_nuplan_reference_files": nuplan_references,
            "fixed_dp_nuplan_closed_loop_adapter_present": fixed_dp_nuplan_adapter,
            "matched_closed_loop_harness_present": False,
        },
        "bounded_proxy_boundary": {
            "protocol": "camp_dp_bounded_offline_safety_score_v1",
            "observable_scope": "frozen_32_dynamic_plus_5_static_only",
            "complete_scene_claim": False,
            "closed_loop_claim": False,
        },
        "gates": {
            "read_only_audit_complete": True,
            "native_top1_provenance_gate": False,
            "native_default_source_provenance_gate": contracts_passed,
            "matched_closed_loop_execution_ready": simulator_ready and contracts_passed,
            "closed_loop_claim_authorized": False,
            "broad_native_top1_claim_authorized": False,
        },
        "data_access": {
            "holdout_reopened": False,
            "holdout_labels_read": 0,
            "simulator_executed": False,
            "new_data_downloaded": False,
        },
        "minimum_gaps": [
            "no executable native K-ranking/Top-1 path is proven in fixed-DP inference",
            "official nuPlan devkit/simulator is unavailable in the fixed DP environment",
            "no CAMP-side matched closed-loop planner adapter/harness is present",
            "SafetyCost v1 and official nuPlan metric extraction are not wired to paired rollouts",
        ],
        "decision": {
            "status": "v19_native_baseline_provenance_and_safety_evidence_gap_audit_complete_execution_not_ready",
            "next_work_target": "v19_native_default_executable_provenance_and_nuplan_closed_loop_capability_plan_only",
        },
    }


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ModuleNotFoundError):
        return False


def render_markdown(report: dict[str, Any]) -> str:
    claims = report["claim_taxonomy"]
    provenance = report["native_baseline_provenance"]
    capability = report["nuplan_capability"]
    gates = report["gates"]
    lines = [
        "# V19 Native Baseline and Safety Evidence Gap Audit",
        "",
        "This is a read-only capability audit. It did not execute a simulator "
        "or open the v18 holdout.",
        "",
        "## Claim Taxonomy",
        "",
        f"- Performance: `{claims['performance_claim']}`",
        "- Bounded offline safety proxy improvement: "
        f"`{claims['bounded_offline_safety_proxy_improvement']}`",
        f"- Closed-loop safety: `{claims['closed_loop_safety_claim']}`",
        "- Broad CAMP over native DP Top-1: "
        f"`{claims['broad_CAMP_over_native_DP_Top1_claim']}`",
        "",
        "## Native Baseline Provenance",
        "",
        f"- Baseline: `{provenance['baseline_name']}`",
        f"- Native ranked Top-1 proven: `{provenance['native_ranked_top1']}`",
        "- Candidate 0 is native Top-1: "
        f"`{provenance['candidate0_is_native_top1']}`",
        "- Native inference source contracts passed: "
        f"`{provenance['native_inference_source_contracts_passed']}`",
        "",
        "## nuPlan Capability",
        "",
        f"- Database count: `{capability['database_count']}`",
        f"- Database bytes: `{capability['database_bytes']}`",
        f"- nuPlan devkit available: `{capability['nuplan_devkit_available']}`",
        "- Official nuPlan simulator available: "
        f"`{capability['official_nuplan_simulator_available']}`",
        "- Matched closed-loop execution ready: "
        f"`{gates['matched_closed_loop_execution_ready']}`",
        "",
        "## Minimum Gaps",
        "",
    ]
    lines.extend(f"- {gap}" for gap in report["minimum_gaps"])
    lines.extend(
        [
            "",
            "## Source Hashes",
            "",
            "| Fixed-DP source | SHA256 | Git blob SHA1 |",
            "| --- | --- | --- |",
        ]
    )
    for item in provenance["source_files"]:
        lines.append(
            f"| `{item['path']}` | `{item['sha256']}` | "
            f"`{item['git_blob_sha1']}` |"
        )
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camp_repo", type=Path, required=True)
    parser.add_argument("--dp_repo", type=Path, required=True)
    parser.add_argument("--nuplan_data_root", type=Path, required=True)
    parser.add_argument("--camp_head", required=True)
    parser.add_argument("--dp_head", required=True)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        camp_repo=args.camp_repo,
        dp_repo=args.dp_repo,
        nuplan_data_root=args.nuplan_data_root,
        camp_head=args.camp_head,
        dp_head=args.dp_head,
        nuplan_devkit_available=_module_available("nuplan"),
        official_nuplan_simulator_available=_module_available(
            "nuplan.planning.simulation"
        ),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
