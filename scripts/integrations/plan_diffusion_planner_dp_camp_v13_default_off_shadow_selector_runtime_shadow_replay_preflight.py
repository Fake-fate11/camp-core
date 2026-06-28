#!/usr/bin/env python3
"""Preflight a v13 default-off CAMP shadow replay command.

This tool is deliberately static: it reads the runtime artifact manifest,
runner source, audit boundary, and candidate replay paths, then writes a JSON/MD
preflight report. It does not execute replay, generate candidates, train CAMP,
modify Diffusion Planner, promote selectors/atoms, deploy, or make safety
claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_VERSION = (
    "dp_camp_v13_default_off_shadow_selector_runtime_shadow_replay_preflight_v1"
)
DISABLED_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_runtime_shadow_replay_preflight_disabled"
)
READY_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_runtime_shadow_replay_preflight_ready"
)
REJECT_STATUS = (
    "dp_camp_v13_default_off_shadow_selector_runtime_shadow_replay_preflight_rejected"
)
AUTHORIZED_NEXT_WORK = (
    "dp_camp_v13_default_off_shadow_selector_runtime_shadow_replay_execution_only"
)
FIXED_DP_HEAD = "7a1d33da277a1992ec474b5383a0c963c72e04e4"
RUNTIME_MANIFEST_SCHEMA_VERSION = "dp_camp_v13_default_off_shadow_selector_runtime_v1"
SCORE_EXPRESSION = "score_k(w)=a_k^T w"
EXPECTED_CANDIDATE_COUNT = 8
FORMAL_SEEDS = (11, 12, 13)

FORBIDDEN_COMMAND_FLAGS = (
    "--candidate_reference_blend_steps",
    "--candidate_guidance_config",
    "--candidate_guidance_scale",
    "--camp_traffic_light_hybrid_postselection",
    "--camp_underprogress_relaxation",
    "--camp_splice_shadow_rule",
)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Static preflight for one default-off CAMP shadow replay command. "
            "It writes a report only and does not execute replay."
        )
    )
    parser.add_argument("--runtime_manifest_json", type=Path, required=True)
    parser.add_argument("--replay_runner_py", type=Path, required=True)
    parser.add_argument("--v13_audit_md", type=Path, required=True)
    parser.add_argument("--diffusion_repo", type=Path, required=True)
    parser.add_argument("--route_name", required=True)
    parser.add_argument("--route_path", type=Path, required=True)
    parser.add_argument("--model_path", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--planned_replay_output_dir", type=Path, required=True)
    parser.add_argument("--current_camp_head", required=True)
    parser.add_argument("--current_camp_origin_main", required=True)
    parser.add_argument("--current_dp_head", required=True)
    parser.add_argument("--required_dp_head", default=FIXED_DP_HEAD)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--formal_seeds", default="11,12,13")
    parser.add_argument("--max_npcs", type=int, default=0)
    parser.add_argument("--spawn_probability", type=float, default=0.3)
    parser.add_argument("--traffic_lights", choices=("off", "on", "config"), default="off")
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--num_candidates", type=int, default=EXPECTED_CANDIDATE_COUNT)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--label", default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    parser.add_argument(
        "--enable_v13_default_off_shadow_selector_runtime_shadow_replay_preflight",
        action="store_true",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    report = build_report(
        runtime_manifest_json=args.runtime_manifest_json,
        replay_runner_py=args.replay_runner_py,
        v13_audit_md=args.v13_audit_md,
        diffusion_repo=args.diffusion_repo,
        route_name=args.route_name,
        route_path=args.route_path,
        model_path=args.model_path,
        config=args.config,
        planned_replay_output_dir=args.planned_replay_output_dir,
        current_camp_head=args.current_camp_head,
        current_camp_origin_main=args.current_camp_origin_main,
        current_dp_head=args.current_dp_head,
        required_dp_head=args.required_dp_head,
        seed=args.seed,
        formal_seeds=_parse_formal_seeds(args.formal_seeds),
        max_npcs=args.max_npcs,
        spawn_probability=args.spawn_probability,
        traffic_lights=args.traffic_lights,
        steps=args.steps,
        num_candidates=args.num_candidates,
        device=args.device,
        label=args.label,
        enabled=bool(
            args.enable_v13_default_off_shadow_selector_runtime_shadow_replay_preflight
        ),
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(_stable(report), indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(_markdown(report), encoding="utf-8")
    print(json.dumps(_stable(report["final_decision"]), indent=2))
    return 0 if report["final_decision"]["passed"] else 1


def build_report(
    *,
    runtime_manifest_json: Path,
    replay_runner_py: Path,
    v13_audit_md: Path,
    diffusion_repo: Path,
    route_name: str,
    route_path: Path,
    model_path: Path,
    config: Path,
    planned_replay_output_dir: Path,
    current_camp_head: str,
    current_camp_origin_main: str,
    current_dp_head: str,
    required_dp_head: str = FIXED_DP_HEAD,
    seed: int,
    formal_seeds: tuple[int, ...] = FORMAL_SEEDS,
    max_npcs: int = 0,
    spawn_probability: float = 0.3,
    traffic_lights: str = "off",
    steps: int = 100,
    num_candidates: int = EXPECTED_CANDIDATE_COUNT,
    device: str = "cuda",
    label: str | None = None,
    enabled: bool,
) -> dict[str, Any]:
    base = {
        "schema_version": SCHEMA_VERSION,
        "analysis": {
            "enabled": bool(enabled),
            "label": label,
            "static_preflight_only": True,
            "runtime_execution": False,
            "replay_execution": False,
            "candidate_generation_execution": False,
            "training_execution": False,
            "dp_modification_execution": False,
            "current_camp_head": current_camp_head,
            "current_camp_origin_main": current_camp_origin_main,
            "current_dp_head": current_dp_head,
            "required_dp_head": required_dp_head,
        },
        "blocked_actions": _blocked_actions(),
        "planned_command": [],
        "review_checks": [],
    }
    if not enabled:
        base["final_decision"] = _decision(False, [], enabled=False)
        base["final_decision"]["status"] = DISABLED_STATUS
        return base

    manifest, manifest_error = _load_json(runtime_manifest_json, "runtime_manifest")
    runner_text = _read_text(replay_runner_py)
    audit_text = _read_text(v13_audit_md)

    artifacts = _dict(manifest.get("artifacts"))
    atom_scales = _dict(artifacts.get("atom_scales"))
    static_weights = _dict(artifacts.get("static_weights"))
    atom_scales_path = Path(str(atom_scales.get("path", "")))
    static_weights_path = Path(str(static_weights.get("path", "")))

    command = _planned_command(
        replay_runner_py=replay_runner_py,
        diffusion_repo=diffusion_repo,
        route_path=route_path,
        model_path=model_path,
        config=config,
        planned_replay_output_dir=planned_replay_output_dir,
        device=device,
        steps=steps,
        seed=seed,
        max_npcs=max_npcs,
        spawn_probability=spawn_probability,
        traffic_lights=traffic_lights,
        num_candidates=num_candidates,
        atom_scales_path=atom_scales_path,
        static_weights_path=static_weights_path,
        runtime_manifest_json=runtime_manifest_json,
    )

    checks: list[dict[str, Any]] = [
        _check("current_camp_head_is_sha", _is_git_sha(current_camp_head), current_camp_head, "40-char git sha"),
        _expect("current_camp_head_matches_origin", current_camp_head, current_camp_origin_main),
        _expect("current_dp_head_fixed", current_dp_head, FIXED_DP_HEAD),
        _expect("required_dp_head_fixed", required_dp_head, FIXED_DP_HEAD),
        _check("seed_is_nonformal", seed not in formal_seeds, seed, f"not in {formal_seeds}"),
        _expect("num_candidates", num_candidates, EXPECTED_CANDIDATE_COUNT),
        _check("steps_positive", steps > 0, steps, "> 0"),
        _check("max_npcs_nonnegative", max_npcs >= 0, max_npcs, ">= 0"),
        _check(
            "spawn_probability_in_unit_interval",
            0.0 <= spawn_probability <= 1.0,
            spawn_probability,
            "[0, 1]",
        ),
        _expect("traffic_lights_off", traffic_lights, "off"),
        _check("diffusion_repo_exists", diffusion_repo.is_dir(), str(diffusion_repo), "directory exists"),
        _check("route_path_exists", route_path.is_file(), str(route_path), "file exists"),
        _check("model_path_exists", model_path.is_file(), str(model_path), "file exists"),
        _check("config_exists", config.is_file(), str(config), "file exists"),
        _check(
            "planned_output_absent",
            not planned_replay_output_dir.exists(),
            str(planned_replay_output_dir),
            "absent before replay",
        ),
        _check("runtime_manifest_readable", manifest_error is None, manifest_error, None),
        _expect("manifest_schema", manifest.get("schema_version"), RUNTIME_MANIFEST_SCHEMA_VERSION),
        _expect("manifest_default_off", manifest.get("default_off"), True),
        _expect("manifest_selection_effect", manifest.get("selection_effect"), False),
        _expect("manifest_candidate_operation", manifest.get("candidate_operation"), "fixed DP candidate reranking only"),
        _expect("manifest_executed_output_policy", manifest.get("executed_output_policy"), "dp_top1"),
        _expect("manifest_score_expression", manifest.get("score_expression"), SCORE_EXPRESSION),
        _expect("manifest_selector_mode", manifest.get("selector_mode"), "static"),
        _expect("manifest_required_candidate_count", manifest.get("required_candidate_count"), EXPECTED_CANDIDATE_COUNT),
        _expect("manifest_current_dp_head", manifest.get("current_dp_head"), FIXED_DP_HEAD),
        _expect("manifest_required_dp_head", manifest.get("required_dp_head"), FIXED_DP_HEAD),
        _expect("manifest_artifact_keys", sorted(artifacts.keys()), ["atom_scales", "static_weights"]),
    ]
    checks.extend(_artifact_checks("atom_scales", atom_scales))
    checks.extend(_artifact_checks("static_weights", static_weights))
    checks.extend(_runner_checks(runner_text))
    checks.extend(_audit_checks(audit_text))
    checks.extend(_command_checks(command))

    failed = [check["name"] for check in checks if not check["passed"]]
    passed = not failed
    base.update(
        {
            "source_hashes": {
                "runtime_manifest_sha256": _sha256(runtime_manifest_json)
                if runtime_manifest_json.is_file()
                else None,
                "replay_runner_sha256": _sha256(replay_runner_py)
                if replay_runner_py.is_file()
                else None,
                "v13_audit_sha256": _sha256(v13_audit_md)
                if v13_audit_md.is_file()
                else None,
            },
            "preflight": {
                "route_name": route_name,
                "route_path": str(route_path),
                "seed": seed,
                "formal_seeds": list(formal_seeds),
                "seed_is_formal": seed in formal_seeds,
                "max_npcs": max_npcs,
                "spawn_probability": spawn_probability,
                "traffic_lights": traffic_lights,
                "steps": steps,
                "num_candidates": num_candidates,
                "planned_replay_output_dir": str(planned_replay_output_dir),
                "planned_output_absent": not planned_replay_output_dir.exists(),
                "runtime_manifest": str(runtime_manifest_json),
                "manifest_sha256": _sha256(runtime_manifest_json)
                if runtime_manifest_json.is_file()
                else None,
                "atom_scales_path": str(atom_scales_path),
                "atom_scales_sha256": atom_scales.get("sha256"),
                "static_weights_path": str(static_weights_path),
                "static_weights_sha256": static_weights.get("sha256"),
            },
            "planned_command": command,
            "review_checks": checks,
            "final_decision": _decision(passed, failed, enabled=True),
        }
    )
    return base


def _planned_command(
    *,
    replay_runner_py: Path,
    diffusion_repo: Path,
    route_path: Path,
    model_path: Path,
    config: Path,
    planned_replay_output_dir: Path,
    device: str,
    steps: int,
    seed: int,
    max_npcs: int,
    spawn_probability: float,
    traffic_lights: str,
    num_candidates: int,
    atom_scales_path: Path,
    static_weights_path: Path,
    runtime_manifest_json: Path,
) -> list[str]:
    return [
        "python",
        str(replay_runner_py),
        "--diffusion_repo",
        str(diffusion_repo),
        "--route",
        str(route_path),
        "--model_path",
        str(model_path),
        "--config",
        str(config),
        "--output_dir",
        str(planned_replay_output_dir),
        "--device",
        device,
        "--steps",
        str(steps),
        "--seed",
        str(seed),
        "--max_npcs",
        str(max_npcs),
        "--spawn_probability",
        f"{spawn_probability:g}",
        "--traffic_lights",
        traffic_lights,
        "--camp_selector_mode",
        "static",
        "--camp_fallback_mode",
        "learned",
        "--camp_feasibility_source",
        "dp_reward",
        "--camp_atom_scales",
        str(atom_scales_path),
        "--camp_static_weights",
        str(static_weights_path),
        "--camp_default_off_shadow_selector",
        "--camp_shadow_artifact_manifest",
        str(runtime_manifest_json),
        "--num_candidates",
        str(num_candidates),
    ]


def _artifact_checks(name: str, entry: dict[str, Any]) -> list[dict[str, Any]]:
    path_text = entry.get("path")
    expected_sha = entry.get("sha256")
    path = Path(str(path_text or ""))
    checks = [
        _expect(f"{name}_logical_name", entry.get("logical_name"), name),
        _expect(f"{name}_required", entry.get("required"), True),
        _check(f"{name}_sha256_valid", _is_sha256(expected_sha), expected_sha, "sha256"),
        _check(f"{name}_path_exists", path.is_file(), str(path), "file exists"),
    ]
    if path.is_file() and _is_sha256(expected_sha):
        checks.append(_expect(f"{name}_sha256_matches", _sha256(path), expected_sha))
    return checks


def _runner_checks(source: str) -> list[dict[str, Any]]:
    return [
        _contains(
            "runner_has_shadow_flag",
            source,
            'parser.add_argument(\n        "--camp_default_off_shadow_selector"',
        ),
        _contains(
            "runner_has_shadow_manifest_arg",
            source,
            'parser.add_argument(\n        "--camp_shadow_artifact_manifest"',
        ),
        _contains("runner_loads_artifact_manifest", source, "def _load_shadow_artifact_manifest"),
        _contains("runner_expected_sha_lookup", source, "def _manifest_expected_sha256"),
        _contains("runner_shadow_forces_dp_top1", source, '"executed_output_policy": "dp_top1"'),
        _contains("runner_records_shadow_selected_index", source, "shadow_selected_index"),
        _contains(
            "runner_rejects_incompatible_shadow_flags",
            source,
            "--camp_default_off_shadow_selector cannot be combined",
        ),
    ]


def _audit_checks(text: str) -> list[dict[str, Any]]:
    return [
        _contains(
            "audit_current_scope_authorizes_preflight",
            text,
            "next_work_target=dp_camp_v13_default_off_shadow_selector_runtime_shadow_replay_preflight_only",
        ),
        _contains(
            "audit_runtime_manifest_materialized",
            text,
            "current_v13_status=current_source_default_off_shadow_selector_runtime_artifact_manifest_materialized",
        ),
        _contains(
            "audit_runtime_execution_blocked",
            text,
            "runtime_shadow_selector_execution_authorized=False",
        ),
        _contains(
            "audit_training_blocked_by_current_boundary",
            text,
            "training_execution_authorized_by_current_boundary=False",
        ),
    ]


def _command_checks(command: list[str]) -> list[dict[str, Any]]:
    joined = " ".join(command)
    return [
        _check(
            "command_uses_shadow_selector",
            "--camp_default_off_shadow_selector" in command,
            joined,
            "shadow flag present",
        ),
        _check(
            "command_uses_shadow_manifest",
            "--camp_shadow_artifact_manifest" in command,
            joined,
            "manifest flag present",
        ),
        _check(
            "command_selector_mode_static",
            _argument_value(command, "--camp_selector_mode") == "static",
            _argument_value(command, "--camp_selector_mode"),
            "static",
        ),
        _check(
            "command_fallback_mode_learned",
            _argument_value(command, "--camp_fallback_mode") == "learned",
            _argument_value(command, "--camp_fallback_mode"),
            "learned",
        ),
        _check(
            "command_feasibility_source_dp_reward",
            _argument_value(command, "--camp_feasibility_source") == "dp_reward",
            _argument_value(command, "--camp_feasibility_source"),
            "dp_reward",
        ),
        _check(
            "command_has_no_guidance_or_reference_blend",
            all(flag not in command for flag in FORBIDDEN_COMMAND_FLAGS[:3]),
            joined,
            "no guidance/blend flags",
        ),
        _check(
            "command_has_no_postselection_relaxation_or_splice",
            all(flag not in command for flag in FORBIDDEN_COMMAND_FLAGS[3:]),
            joined,
            "no postselection/relaxation/splice flags",
        ),
    ]


def _decision(passed: bool, failed_checks: list[str], *, enabled: bool) -> dict[str, Any]:
    return {
        "status": READY_STATUS if passed else REJECT_STATUS,
        "enabled": enabled,
        "passed": bool(passed),
        "failed_checks": failed_checks,
        "authorized_next_work": AUTHORIZED_NEXT_WORK if passed else None,
        "shadow_replay_execution_authorized_next": bool(passed),
        "runtime_shadow_selector_execution_authorized_by_this_gate": False,
        "replay_execution_performed": False,
        "candidate_generation_executed": False,
        "candidate_generation_by_camp_authorized": False,
        "formal_seeds_authorized": False,
        "dp_modification_authorized": False,
        "training_executed": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }


def _blocked_actions() -> dict[str, bool]:
    return {
        "runtime_shadow_selector_execution_authorized_by_this_gate": False,
        "replay_execution_performed": False,
        "candidate_generation_executed": False,
        "candidate_generation_by_camp_authorized": False,
        "formal_seeds_authorized": False,
        "dp_modification_authorized": False,
        "training_executed": False,
        "selector_promotion_authorized": False,
        "atom_promotion_authorized": False,
        "deployment_authorized": False,
        "safety_benefit_claim_authorized": False,
        "camp_over_dp_top1_claim_authorized": False,
    }


def _markdown(report: dict[str, Any]) -> str:
    decision = report["final_decision"]
    lines = [
        "# V13 Default-Off Shadow Replay Preflight",
        "",
        f"- Status: `{decision['status']}`",
        f"- Passed: `{decision['passed']}`",
        f"- Authorized next work: `{decision['authorized_next_work']}`",
        f"- Failed checks: `{','.join(decision['failed_checks'])}`",
        "",
        "This is a static preflight only. It does not execute replay, generate "
        "candidates, train CAMP, modify DP, promote, deploy, or authorize "
        "safety/CAMP-over-DP claims.",
        "",
        "## Planned Command",
        "",
        "```text",
        " ".join(report.get("planned_command", [])),
        "```",
    ]
    return "\n".join(lines) + "\n"


def _load_json(path: Path, name: str) -> tuple[dict[str, Any], str | None]:
    if not path.is_file():
        return {}, f"{name}_missing"
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, f"{name}_unreadable"
    if not isinstance(loaded, dict):
        return {}, f"{name}_not_object"
    return loaded, None


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _parse_formal_seeds(value: str) -> tuple[int, ...]:
    seeds = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    return seeds


def _argument_value(command: list[str], flag: str) -> str | None:
    try:
        index = command.index(flag)
    except ValueError:
        return None
    value_index = index + 1
    if value_index >= len(command):
        return None
    return command[value_index]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _contains(name: str, text: str, needle: str) -> dict[str, Any]:
    return _check(name, needle in text, "present" if needle in text else "missing", needle)


def _expect(name: str, observed: Any, expected: Any) -> dict[str, Any]:
    return _check(name, observed == expected, observed, expected)


def _check(name: str, passed: bool, observed: Any, expected: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "observed": observed,
        "expected": expected,
    }


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


def _is_git_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value.lower())


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())


if __name__ == "__main__":
    raise SystemExit(main())
