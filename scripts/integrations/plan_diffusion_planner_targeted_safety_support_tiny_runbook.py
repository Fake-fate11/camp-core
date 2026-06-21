#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path
from typing import Any


SOURCE_READY_STATUS = "targeted_safety_support_scenario_or_source_design_ready"
SOURCE_READY_NEXT_WORK = "targeted_safety_support_tiny_runbook_preflight_only"
READY_STATUS = "targeted_safety_support_tiny_runbook_preflight_ready"
REJECT_STATUS = "targeted_safety_support_tiny_runbook_preflight_rejected"
AUTHORIZED_NEXT_WORK = "targeted_safety_support_tiny_nonformal_execution_only"

EXPECTED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
FORMAL_SEEDS = {11, 12, 13}

DEFAULT_CAMP_REPO = "/root/autodl-tmp/camp_core"
DEFAULT_DIFFUSION_REPO = "/root/autodl-tmp/Diffusion-Planner"
DEFAULT_OUTPUT_ROOT = "/root/autodl-tmp/camp_dp_targeted_safety_support_tiny"
DEFAULT_MODEL_PATH = "/root/autodl-tmp/camp_dp_assets/diffusion_planner.pth"
DEFAULT_MODEL_ARGS = "/root/autodl-tmp/camp_dp_assets/diffusion_planner.param.json"
DEFAULT_CONFIG = (
    "/root/autodl-tmp/Diffusion-Planner/scenario_generation/configs/replay_default.json"
)
DEFAULT_REWARD_CONFIG = (
    "/root/autodl-tmp/camp_core/configs/integrations/dp_camp_reward_eval.json"
)
DEFAULT_ATOM_SCALES = (
    "/root/autodl-tmp/camp_dp_assets/"
    "camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/"
    "atom_scales_dp_static.json"
)
DEFAULT_STATIC_WEIGHTS = (
    "/root/autodl-tmp/camp_dp_assets/"
    "camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/"
    "offline_weights_dp_static.npy"
)
DEFAULT_SAFETY_PROXY_SOURCE = (
    "/root/autodl-tmp/camp_dp_development_perfect_v10_redstopfloor05_e70f263/"
    "temporal_consistency_shadow_safety_proxy_db49745/"
    "temporal_consistency_shadow_safety_proxy.json"
)
MAP_PATHS = {
    "sample_map": (
        "/root/autodl-tmp/camp_dp_assets/sample-map-planning/"
        "sample-map-planning/lanelet2_map_no_ros.osm"
    ),
    "nishishinjuku": "/root/autodl-tmp/camp_dp_assets/nishishinjuku_no_ros.osm",
}

BLOCKED_ACTIONS = (
    "training_execution_authorized",
    "camp_retraining_authorized",
    "online_selector_authorized",
    "online_selector_promotion_authorized",
    "closed_loop_replay_authorized",
    "closed_loop_smoke_authorized",
    "full36_authorized",
    "formal_seeds_authorized",
    "dp_modification_authorized",
    "classic_benders_claim_authorized",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Runbook preflight for the targeted safety support tiny nonformal "
            "discovery. This writes commands only and does not execute replay."
        )
    )
    parser.add_argument("--design_json", type=Path, required=True)
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--camp_repo", default=DEFAULT_CAMP_REPO)
    parser.add_argument("--diffusion_repo", default=DEFAULT_DIFFUSION_REPO)
    parser.add_argument("--safety_proxy_json", default=DEFAULT_SAFETY_PROXY_SOURCE)
    parser.add_argument("--check_assets", action="store_true")
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument("--output_bash", type=Path, required=True)
    parser.add_argument("--require_pass", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        design_report=_load_json(args.design_json),
        label=args.label,
        output_root=args.output_root,
        camp_repo=args.camp_repo,
        diffusion_repo=args.diffusion_repo,
        safety_proxy_json=args.safety_proxy_json,
        check_assets=args.check_assets,
        paths={"design_json": str(args.design_json)},
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_bash.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    args.output_bash.write_text(render_bash(report), encoding="utf-8")
    print(json.dumps(report["final_decision"], indent=2, sort_keys=True))
    if args.require_pass and not report["final_decision"]["passed"]:
        raise SystemExit(1)


def build_report(
    *,
    design_report: dict[str, Any],
    label: str | None = None,
    output_root: str = DEFAULT_OUTPUT_ROOT,
    camp_repo: str = DEFAULT_CAMP_REPO,
    diffusion_repo: str = DEFAULT_DIFFUSION_REPO,
    safety_proxy_json: str = DEFAULT_SAFETY_PROXY_SOURCE,
    check_assets: bool = False,
    paths: dict[str, str] | None = None,
) -> dict[str, Any]:
    source = _source_summary(design_report)
    manifest = _manifest(
        design_report=design_report,
        output_root=output_root,
        camp_repo=camp_repo,
        diffusion_repo=diffusion_repo,
        safety_proxy_json=safety_proxy_json,
    )
    commands = _commands(manifest)
    checks = [
        *_source_checks(source),
        *_manifest_checks(manifest),
        *_asset_checks(manifest, enabled=check_assets),
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "analysis": {
            "name": "dp_camp_targeted_safety_support_tiny_runbook_v1",
            "label": label,
            "role": (
                "preflight-only runbook for tiny nonformal targeted safety support "
                "discovery"
            ),
            "training": False,
            "online_selector_change": False,
            "closed_loop_replay": False,
            "diffusion_planner_execution": False,
            "diffusion_planner_modification": False,
            "future_outcome_labels_used": False,
            "selection_effect": False,
            "check_assets": bool(check_assets),
            "paths": paths or {},
            "math_boundary": (
                "This runbook preflight only serializes commands and checks the "
                "design contract. It does not execute DP replay, train CAMP, or "
                "change online selection. The later replay, if separately executed, "
                "must keep all candidate source fields current-tick and fixed before "
                "CAMP scoring. The proposed gap-to-best safety coefficients are "
                "nonnegative by construction; if atomized after evidence, "
                "score_k(w)=a_k^T w remains affine and the simplex/CVaR/L2 robust "
                "master remains convex. No DP-side classical Benders decomposition "
                "is introduced."
            ),
        },
        "source_design": source,
        "runbook_manifest": manifest,
        "commands": commands,
        "runbook_checks": checks,
        "accept_criteria": _accept_criteria(manifest),
        "reject_criteria": _reject_criteria(),
        "blocked_actions": {key: False for key in BLOCKED_ACTIONS},
        "final_decision": _final_decision(passed, checks, manifest),
    }


def _source_summary(report: dict[str, Any]) -> dict[str, Any]:
    final = _dict(report.get("final_decision"))
    design = _dict(report.get("design_contract"))
    conflicts = [key for key in BLOCKED_ACTIONS if bool(final.get(key))]
    return {
        "status": final.get("status"),
        "passed": bool(final.get("passed")),
        "authorized_next_work": final.get("authorized_next_work"),
        "tiny_support_row_count": int(final.get("tiny_support_row_count", -1)),
        "candidate_source_family_count": int(
            final.get("candidate_source_family_count", -1)
        ),
        "existing_source_atomization_authorized": bool(
            final.get("existing_source_atomization_authorized")
        ),
        "blocked_action_conflicts": conflicts,
        "rows": list(_dict(design.get("tiny_support_discovery")).get("rows") or []),
        "candidate_source_families": list(design.get("candidate_source_families") or []),
    }


def _manifest(
    *,
    design_report: dict[str, Any],
    output_root: str,
    camp_repo: str,
    diffusion_repo: str,
    safety_proxy_json: str,
) -> dict[str, Any]:
    source = _source_summary(design_report)
    rows = []
    for raw in source["rows"]:
        route_name = str(raw["route_name"])
        map_key = "nishishinjuku" if route_name.startswith("nishi") else "sample_map"
        run_id = str(raw["name"])
        rows.append(
            {
                "run_id": run_id,
                "map_key": map_key,
                "map_path": MAP_PATHS[map_key],
                "route_name": route_name,
                "route": str(raw["route_asset"]),
                "seed": int(raw["seed"]),
                "max_npcs": int(raw["max_npcs"]),
                "spawn_probability": float(raw["spawn_probability"]),
                "traffic_lights": "on" if bool(raw["traffic_lights"]) else "off",
                "buckets": [str(item) for item in raw["buckets"]],
                "output_dir": f"{output_root}/logging_enabled/{run_id}",
            }
        )
    return {
        "schema_version": "targeted_safety_support_tiny_runbook_v1",
        "camp_repo": camp_repo,
        "diffusion_repo": diffusion_repo,
        "expected_dp_head": EXPECTED_DP_HEAD,
        "output_root": output_root,
        "logging_root": f"{output_root}/logging_enabled",
        "audit_root": f"{output_root}/audit",
        "safety_proxy_json": safety_proxy_json,
        "model_path": DEFAULT_MODEL_PATH,
        "model_args": DEFAULT_MODEL_ARGS,
        "config": DEFAULT_CONFIG,
        "reward_config": DEFAULT_REWARD_CONFIG,
        "atom_scales": DEFAULT_ATOM_SCALES,
        "static_weights": DEFAULT_STATIC_WEIGHTS,
        "steps": 10,
        "num_candidates": 8,
        "rows": rows,
    }


def _commands(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "asset_audit": _asset_audit_command(manifest),
        "head_audit": _head_audit_command(manifest),
        "replays": [
            {"run_id": row["run_id"], "command": _replay_command(manifest, row)}
            for row in manifest["rows"]
        ],
        "dataset_audit": _dataset_audit_command(manifest),
        "materiality_audit": _materiality_audit_command(manifest),
    }


def _asset_audit_command(manifest: dict[str, Any]) -> list[str]:
    assets = sorted(
        {
            manifest["model_path"],
            manifest["model_args"],
            manifest["config"],
            manifest["reward_config"],
            manifest["atom_scales"],
            manifest["static_weights"],
            manifest["safety_proxy_json"],
            *(row["map_path"] for row in manifest["rows"]),
            *(row["route"] for row in manifest["rows"]),
        }
    )
    tests = " && ".join(f"test -f {shlex.quote(path)}" for path in assets)
    return ["/bin/bash", "-lc", f"{tests} && echo targeted_support_assets_ok"]


def _head_audit_command(manifest: dict[str, Any]) -> list[str]:
    return [
        "/bin/bash",
        "-lc",
        (
            f'test "$(git -C {manifest["camp_repo"]} rev-parse HEAD)" = '
            f'"$(git -C {manifest["camp_repo"]} rev-parse origin/main)" && '
            f'test "$(git -C {manifest["diffusion_repo"]} rev-parse HEAD)" = '
            f'"{manifest["expected_dp_head"]}" && '
            f'echo "CAMP_HEAD=$(git -C {manifest["camp_repo"]} rev-parse HEAD)" && '
            f'echo "DP_HEAD=$(git -C {manifest["diffusion_repo"]} rev-parse HEAD)"'
        ),
    ]


def _replay_command(manifest: dict[str, Any], row: dict[str, Any]) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "REPLAY_NO_PNG=1",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/run_diffusion_planner_camp_replay.py",
        "--diffusion_repo",
        manifest["diffusion_repo"],
        "--map_path",
        row["map_path"],
        "--route",
        row["route"],
        "--model_path",
        manifest["model_path"],
        "--model_args",
        manifest["model_args"],
        "--config",
        manifest["config"],
        "--output_dir",
        row["output_dir"],
        "--device",
        "cuda",
        "--advance_mode",
        "perfect",
        "--steps",
        str(manifest["steps"]),
        "--seed",
        str(row["seed"]),
        "--max_npcs",
        str(row["max_npcs"]),
        "--spawn_probability",
        str(row["spawn_probability"]),
        "--traffic_lights",
        row["traffic_lights"],
        "--reward_config",
        manifest["reward_config"],
        "--camp_selector_mode",
        "static",
        "--camp_atom_scales",
        manifest["atom_scales"],
        "--camp_static_weights",
        manifest["static_weights"],
        "--num_candidates",
        str(manifest["num_candidates"]),
        "--candidate_noise_scale",
        "1.0",
        "--candidate_reference_blend_steps",
        "5",
        "--camp_lane_corridor_buffer",
        "1.0",
        "--camp_feasibility_source",
        "dp_reward",
        "--camp_fallback_mode",
        "learned",
        "--camp_min_progress_ratio",
        "0.8",
        "--camp_shadow_route_progress",
        "--camp_shadow_obstacle_clearance",
        "--camp_reward_horizon_steps",
        "30",
        "--camp_outcome_horizon_steps",
        "30",
        "--near_miss_threshold_m",
        "2.0",
    ]


def _dataset_audit_command(manifest: dict[str, Any]) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/audit_diffusion_planner_camp_dataset.py",
        "--root",
        manifest["logging_root"],
        "--atom_scales",
        manifest["atom_scales"],
        "--expected_logs",
        str(len(manifest["rows"])),
        "--expected_candidates",
        str(manifest["num_candidates"]),
        "--expected_advance_mode",
        "perfect",
        "--closed_loop_outcome_policy",
        "forbidden",
        "--forbid_seed",
        "11",
        "--forbid_seed",
        "12",
        "--forbid_seed",
        "13",
        "--require_finite_candidate_contract",
        "--output_json",
        f"{manifest['audit_root']}/dataset_audit.json",
    ]


def _materiality_audit_command(manifest: dict[str, Any]) -> list[str]:
    return [
        "PYTHONPATH=/root/autodl-tmp/camp_core:/root/autodl-tmp/camp_core/camp_core",
        "/root/autodl-tmp/dp312_venv/bin/python",
        "scripts/integrations/analyze_diffusion_planner_alternative_safety_source_materiality.py",
        "--safety_proxy_json",
        manifest["safety_proxy_json"],
        "--candidate_root",
        manifest["logging_root"],
        "--expected_logs",
        str(len(manifest["rows"])),
        "--expected_records",
        str(len(manifest["rows"]) * int(manifest["steps"])),
        "--expected_candidates",
        str(manifest["num_candidates"]),
        "--expected_available_records",
        str(len(manifest["rows"]) * int(manifest["steps"])),
        "--availability_mode",
        "candidate_safety_fields",
        "--label",
        "targeted_safety_support_tiny_materiality",
        "--output_json",
        f"{manifest['audit_root']}/alternative_safety_source_materiality.json",
        "--output_md",
        f"{manifest['audit_root']}/alternative_safety_source_materiality.md",
        "--require_pass",
    ]


def _source_checks(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        _check_equal("source_status", source["status"], SOURCE_READY_STATUS),
        _check_equal("source_passed", source["passed"], True),
        _check_equal(
            "source_authorizes_runbook_preflight",
            source["authorized_next_work"],
            SOURCE_READY_NEXT_WORK,
        ),
        _check_equal("source_no_blocked_actions", source["blocked_action_conflicts"], []),
        _check_equal("source_row_count_matches", source["tiny_support_row_count"], len(source["rows"])),
        _check_equal(
            "source_candidate_families_match",
            source["candidate_source_family_count"],
            len(source["candidate_source_families"]),
        ),
        _check_equal(
            "source_existing_atomization_not_authorized",
            source["existing_source_atomization_authorized"],
            False,
        ),
    ]


def _manifest_checks(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    rows = list(manifest["rows"])
    seeds = [int(row["seed"]) for row in rows]
    formal = sorted(seed for seed in seeds if seed in FORMAL_SEEDS)
    return [
        _check_equal("row_count", len(rows), 5),
        _check_equal("no_formal_seeds", formal, []),
        _check_equal(
            "has_normal_guard",
            any("normal" in row["buckets"] for row in rows),
            True,
        ),
        _check_equal(
            "has_red_light_target",
            any("red_light_turn" in row["buckets"] for row in rows),
            True,
        ),
        _check_equal(
            "has_dense_lane_change_target",
            any("lane_change_or_merge" in row["buckets"] and row["max_npcs"] >= 8 for row in rows),
            True,
        ),
        _check_equal("steps", manifest["steps"], 10),
        _check_equal("num_candidates", manifest["num_candidates"], 8),
    ]


def _asset_checks(manifest: dict[str, Any], *, enabled: bool) -> list[dict[str, Any]]:
    paths = sorted(
        {
            manifest["model_path"],
            manifest["model_args"],
            manifest["config"],
            manifest["reward_config"],
            manifest["atom_scales"],
            manifest["static_weights"],
            manifest["safety_proxy_json"],
            *(row["map_path"] for row in manifest["rows"]),
            *(row["route"] for row in manifest["rows"]),
        }
    )
    if not enabled:
        return [
            {
                "name": "asset_paths_check_skipped",
                "observed": "skipped",
                "expected": "skipped",
                "passed": True,
            }
        ]
    missing = [path for path in paths if not Path(path).is_file()]
    return [_check_equal("asset_paths_exist", missing, [])]


def _final_decision(
    passed: bool,
    checks: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "passed": passed,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "failed_checks": [check["name"] for check in checks if not check["passed"]],
        "recommended_first_action": (
            "execute_targeted_safety_support_tiny_runbook"
            if passed
            else "repair_targeted_safety_support_tiny_runbook_preflight"
        ),
        "run_count": len(manifest["rows"]),
        "expected_records": len(manifest["rows"]) * int(manifest["steps"]),
        "expected_available_records": len(manifest["rows"]) * (int(manifest["steps"]) - 1),
        "new_replay_authorized": passed,
        "closed_loop_replay_authorized": False,
        "training_execution_authorized": False,
        "camp_retraining_authorized": False,
        "online_selector_authorized": False,
        "online_selector_promotion_authorized": False,
        "full36_authorized": False,
        "formal_seeds_authorized": False,
        "dp_modification_authorized": False,
        "classic_benders_claim_authorized": False,
        "next_step": (
            "Execute exactly this 5-run nonformal default-off runbook, then run "
            "dataset and safety-source materiality audits. Do not expand scope."
            if passed
            else "Reject execution until every preflight check passes."
        ),
    }


def _accept_criteria(manifest: dict[str, Any]) -> list[str]:
    return [
        "asset and head audits pass before replay",
        "exactly five nonformal rows are executed",
        "no formal seed 11/12/13 is used",
        "DP commit remains fixed",
        "all output records keep candidate_closed_loop_outcomes forbidden",
        "dataset audit passes finite-candidate contract checks",
        "materiality audit reports whether any current selected candidate is not safety-proxy-best",
        "no online selector, CAMP retraining, Full36, formal seed, or DP modification is introduced",
        f"expected logs={len(manifest['rows'])}, records={len(manifest['rows']) * int(manifest['steps'])}, candidates={manifest['num_candidates']}",
    ]


def _reject_criteria() -> list[str]:
    return [
        "any asset or head audit fails",
        "any command uses a formal seed",
        "any command changes DP/CAMP weights or DP code",
        "any output includes closed-loop outcomes",
        "scope expands beyond the five predeclared rows",
        "dataset or materiality audit fails",
    ]


def render_markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    manifest = report["runbook_manifest"]
    lines = [
        "# Targeted Safety Support Tiny Runbook Preflight",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Run count: `{decision['run_count']}`",
        f"- Expected records: `{decision['expected_records']}`",
        "",
        "## Rows",
        "",
        "| Run | Route | Seed | NPCs | TL | Buckets |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ]
    for row in manifest["rows"]:
        lines.append(
            f"| `{row['run_id']}` | `{row['route_name']}` | `{row['seed']}` | "
            f"`{row['max_npcs']}` | `{row['traffic_lights']}` | "
            f"`{', '.join(row['buckets'])}` |"
        )
    lines.extend(["", "## Commands", ""])
    commands = report["commands"]
    command_separator = " \\\n  "
    for name in ("asset_audit", "head_audit", "dataset_audit", "materiality_audit"):
        lines.extend(
            [
                f"### {name}",
                "",
                "```bash",
                command_separator.join(commands[name]),
                "```",
                "",
            ]
        )
    lines.extend(["### replays", ""])
    for item in commands["replays"]:
        lines.extend(
            [
                f"#### {item['run_id']}",
                "",
                "```bash",
                command_separator.join(item["command"]),
                "```",
                "",
            ]
        )
    lines.extend(["## Accept Criteria", ""])
    lines.extend(f"- {item}" for item in report["accept_criteria"])
    lines.extend(["", "## Reject Criteria", ""])
    lines.extend(f"- {item}" for item in report["reject_criteria"])
    lines.extend(["", "## Mathematical Boundary", "", report["analysis"]["math_boundary"], ""])
    lines.extend(["## Checks", "", "| Check | Passed | Observed | Expected |", "| --- | ---: | --- | --- |"])
    for check in report["runbook_checks"]:
        lines.append(
            f"| `{check['name']}` | `{check['passed']}` | "
            f"`{check.get('observed')}` | `{check.get('expected')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def render_bash(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    if decision.get("authorized_next_work") != AUTHORIZED_NEXT_WORK:
        raise ValueError("Cannot render bash for a rejected targeted support runbook.")
    commands = report["commands"]
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Auto-generated targeted safety support tiny runbook.",
        "# Scope: five nonformal default-off support-discovery runs only.",
        "# Forbidden: formal seeds, Full36, online selector promotion, CAMP retraining, DP modification.",
        f"# Expected DP HEAD: {EXPECTED_DP_HEAD}",
        "",
        "cd /root/autodl-tmp/camp_core",
        "",
    ]
    for name in ("asset_audit", "head_audit"):
        lines.extend([f'echo "== {name} =="', shlex.join(commands[name]), ""])
    for item in commands["replays"]:
        lines.extend(
            [
                f'echo "== replay {item["run_id"]} =="',
                shlex.join(item["command"]),
                "",
            ]
        )
    for name in ("dataset_audit", "materiality_audit"):
        lines.extend([f'echo "== {name} =="', shlex.join(commands[name]), ""])
    lines.extend(['echo "targeted_safety_support_tiny_runbook_complete"', ""])
    return "\n".join(lines)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _check_equal(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "observed": observed,
        "expected": expected,
        "passed": observed == expected,
    }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
