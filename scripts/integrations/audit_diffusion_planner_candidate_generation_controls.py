#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from scripts.integrations.run_diffusion_planner_camp_replay import (  # noqa: E402
    _candidate_generation_contract,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit fixed Diffusion Planner candidate-generation controls and "
            "the CAMP runner boundary without executing Diffusion Planner."
        )
    )
    parser.add_argument("--diffusion_repo", type=Path, required=True)
    parser.add_argument("--model_args", type=Path, required=True)
    parser.add_argument("--camp_root", type=Path, default=ROOT)
    parser.add_argument("--num_candidates", type=int, default=8)
    parser.add_argument("--candidate_noise_scale", type=float, default=1.0)
    parser.add_argument("--candidate_reference_blend_steps", type=int, default=None)
    parser.add_argument("--output_json", type=Path, required=True)
    parser.add_argument("--output_md", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(
        args.diffusion_repo,
        model_args_path=args.model_args,
        camp_root=args.camp_root,
        num_candidates=args.num_candidates,
        candidate_noise_scale=args.candidate_noise_scale,
        candidate_reference_blend_steps=args.candidate_reference_blend_steps,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(render_markdown(report), encoding="utf-8")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")


def analyze(
    diffusion_repo: Path,
    *,
    model_args_path: Path,
    camp_root: Path = ROOT,
    num_candidates: int = 8,
    candidate_noise_scale: float = 1.0,
    candidate_reference_blend_steps: int | None = None,
) -> dict[str, Any]:
    diffusion_repo = diffusion_repo.resolve()
    camp_root = camp_root.resolve()
    model_args_path = model_args_path.resolve()
    if num_candidates < 1:
        raise ValueError("num_candidates must be >= 1.")
    if candidate_noise_scale < 0.0:
        raise ValueError("candidate_noise_scale must be nonnegative.")
    if (
        candidate_reference_blend_steps is not None
        and candidate_reference_blend_steps < 1
    ):
        raise ValueError("candidate_reference_blend_steps must be None or >= 1.")

    files = _required_files(diffusion_repo=diffusion_repo, camp_root=camp_root)
    texts = {name: path.read_text(encoding="utf-8") for name, path in files.items()}
    model_args_payload = _read_model_args(model_args_path)
    model_args = _ObjectView(model_args_payload)
    contract = _candidate_generation_contract(
        model_args,
        num_candidates=num_candidates,
        noise_scale=candidate_noise_scale,
        noise_strategy="iid",
        reference_blend_steps=candidate_reference_blend_steps,
    )
    decoder_controls = _decoder_controls(texts["dp_decoder"])
    camp_controls = _camp_controls(texts["camp_adapter"], texts["camp_runner"])
    guidance = _guidance_inventory(diffusion_repo)

    official_guidance_available = bool(
        guidance["registered_guidance_functions"]
        or guidance["composer_present"]
        or guidance["legacy_wrapper_present"]
    )
    current_guidance_disabled = bool(
        camp_controls["adapter_disables_decoder_guidance"]
        and contract["guidance_enabled"] is False
    )
    prototype_support_available = bool(
        guidance["anchor_following_present"] and guidance["prototype_builder_present"]
    )
    candidate_set_only_if_enabled_later = bool(
        official_guidance_available and current_guidance_disabled
    )

    return {
        "analysis": {
            "name": "dp_candidate_generation_controls_audit_v1",
            "role": (
                "static audit of fixed-DP candidate-generation controls before "
                "any non-formal candidate-set diagnostic"
            ),
            "training": False,
            "online_selector_change": False,
            "diffusion_planner_execution": False,
            "future_outcome_leakage": False,
            "convexity_boundary": (
                "This audit only records generator controls. Any later "
                "sampling, blending, or guidance change must be described as "
                "changing the finite candidate set. For a fixed candidate set, "
                "CAMP scoring remains affine in w and compatible with the "
                "simplex/CVaR/L2 convex master. Guidance/prototype steering is "
                "not Benders and gives no trajectory-coordinate convexity "
                "claim."
            ),
        },
        "inputs": {
            "diffusion_repo": str(diffusion_repo),
            "diffusion_planner_commit": _git_head(diffusion_repo),
            "model_args": str(model_args_path),
            "camp_root": str(camp_root),
            "camp_commit": _git_head(camp_root),
        },
        "model_args_summary": _model_args_summary(model_args_payload),
        "current_contract": contract,
        "decoder_controls": decoder_controls,
        "camp_controls": camp_controls,
        "guidance_inventory": guidance,
        "candidate_set_variables": {
            "currently_exposed": [
                "num_candidates",
                "candidate_noise_scale",
                "candidate_reference_blend_steps",
            ],
            "already_rejected_current_grid": [
                "K16 noise 1.0",
                "K16 noise 0.75",
            ],
            "official_dp_mechanisms_available_but_disabled": [
                "classifier guidance" if official_guidance_available else None,
                "anchor/prototype guidance" if prototype_support_available else None,
            ],
        },
        "admissibility": {
            "fixed_dp_weights_required": True,
            "dp_source_modification_required": False,
            "camp_score_change_required": False,
            "camp_atom_schema_change_required": False,
            "current_runner_guidance_disabled": current_guidance_disabled,
            "official_guidance_available": official_guidance_available,
            "prototype_support_available": prototype_support_available,
            "guidance_can_only_be_next_gate_if_default_off": (
                candidate_set_only_if_enabled_later
            ),
        },
        "next_gate": {
            "decision": (
                "predeclare_default_off_guidance_candidate_set_diagnostic"
                if candidate_set_only_if_enabled_later
                else "reject_guidance_branch_until_mechanism_is_available"
            ),
            "requirements": [
                "no Diffusion Planner source or weight changes",
                "no CAMP weight training",
                "default-off CLI and metadata",
                "strictly report as finite candidate-set change",
                "paired non-formal sample59 seeds only before any formal seeds",
                "reject unless endpoint/mode spread and outcome-free availability improve without latency/comfort regressions",
            ],
        },
    }


class _ObjectView:
    def __init__(self, payload: dict[str, Any]):
        self.__dict__.update(payload)


def _required_files(*, diffusion_repo: Path, camp_root: Path) -> dict[str, Path]:
    files = {
        "dp_decoder": (
            diffusion_repo
            / "diffusion_planner"
            / "diffusion_planner"
            / "model"
            / "module"
            / "decoder.py"
        ),
        "dp_guidance_composer": (
            diffusion_repo
            / "diffusion_planner"
            / "diffusion_planner"
            / "model"
            / "guidance"
            / "composer.py"
        ),
        "dp_anchor_guidance": (
            diffusion_repo
            / "diffusion_planner"
            / "diffusion_planner"
            / "model"
            / "guidance"
            / "anchor_following.py"
        ),
        "dp_prototype_builder": (
            diffusion_repo / "diffusion_planner" / "sampling" / "build_prototypes.py"
        ),
        "camp_adapter": (
            camp_root / "camp_core" / "camp_core" / "integrations" / "diffusion_planner.py"
        ),
        "camp_runner": (
            camp_root / "scripts" / "integrations" / "run_diffusion_planner_camp_replay.py"
        ),
    }
    missing = [str(path) for path in files.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing required audit files: " + ", ".join(missing))
    return files


def _read_model_args(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing model args JSON: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    required = ("future_len", "predicted_neighbor_num")
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"{path} is missing required keys: {missing}")
    return payload


def _decoder_controls(text: str) -> dict[str, Any]:
    steps = _first_int(r"dpm_solver\.sample\([^)]*steps\s*=\s*(\d+)", text)
    skip_type = _first_string(r"dpm_solver\.sample\([^)]*skip_type\s*=\s*['\"]([^'\"]+)", text)
    return {
        "dpm_solver_sample_present": "dpm_solver.sample" in text,
        "dpm_solver_steps": steps,
        "dpm_skip_type": skip_type,
        "guidance_fn_field_present": "_guidance_fn" in text,
        "guidance_type_classifier_present": '"classifier"' in text or "'classifier'" in text,
        "guidance_scale_field_present": "_guidance_scale" in text,
        "prefix_constraint_present": "prefix_constraint" in text,
    }


def _camp_controls(adapter_text: str, runner_text: str) -> dict[str, Any]:
    return {
        "candidate_generation_contract_present": (
            "_candidate_generation_contract" in runner_text
        ),
        "selection_record_contract_logged": (
            '"candidate_generation_contract"' in runner_text
        ),
        "adapter_disables_decoder_guidance": (
            "decoder._guidance_fn = None" in adapter_text
        ),
        "adapter_restores_decoder_guidance": (
            "decoder._guidance_fn = original_guidance" in adapter_text
        ),
        "latent_noise_scale_exposed": "noise_scale" in adapter_text,
        "deterministic_first_exposed": "deterministic_first" in adapter_text,
        "reference_blend_exposed": "reference_blend_steps" in adapter_text,
    }


def _guidance_inventory(diffusion_repo: Path) -> dict[str, Any]:
    guidance_dir = (
        diffusion_repo
        / "diffusion_planner"
        / "diffusion_planner"
        / "model"
        / "guidance"
    )
    registered = []
    if guidance_dir.is_dir():
        for path in sorted(guidance_dir.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            for class_match in re.finditer(r"@register\s+class\s+(\w+)", text):
                class_name = class_match.group(1)
                name_match = re.search(
                    r"class\s+"
                    + re.escape(class_name)
                    + r"\b[\s\S]*?\n\s+name\s*=\s*['\"]([^'\"]+)['\"]",
                    text,
                )
                registered.append(
                    {
                        "module": path.name,
                        "class": class_name,
                        "name": name_match.group(1) if name_match else None,
                    }
                )
    composer = guidance_dir / "composer.py"
    wrapper = guidance_dir / "guidance_wrapper.py"
    anchor = guidance_dir / "anchor_following.py"
    builder = diffusion_repo / "diffusion_planner" / "sampling" / "build_prototypes.py"
    return {
        "registered_guidance_functions": registered,
        "composer_present": composer.is_file(),
        "legacy_wrapper_present": wrapper.is_file(),
        "anchor_following_present": anchor.is_file(),
        "prototype_builder_present": builder.is_file(),
    }


def _model_args_summary(payload: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "diffusion_model_type",
        "future_len",
        "predicted_neighbor_num",
        "guidance_scale",
        "use_velocity_representation",
        "decoder_depth",
        "hidden_dim",
        "num_heads",
    )
    return {key: payload.get(key) for key in keys if key in payload}


def _git_head(path: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def _first_int(pattern: str, text: str) -> int | None:
    match = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
    return int(match.group(1)) if match else None


def _first_string(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
    return match.group(1) if match else None


def render_markdown(report: dict[str, Any]) -> str:
    analysis = report["analysis"]
    inputs = report["inputs"]
    model = report["model_args_summary"]
    controls = report["decoder_controls"]
    camp = report["camp_controls"]
    guidance = report["guidance_inventory"]
    admissibility = report["admissibility"]
    next_gate = report["next_gate"]

    lines = [
        "# DP Candidate Generation Controls Audit",
        "",
        f"- Analysis: `{analysis['name']}`",
        f"- CAMP commit: `{inputs.get('camp_commit')}`",
        f"- Diffusion Planner commit: `{inputs.get('diffusion_planner_commit')}`",
        f"- Model type: `{model.get('diffusion_model_type')}`",
        f"- Future length: `{model.get('future_len')}`",
        f"- Predicted neighbors: `{model.get('predicted_neighbor_num')}`",
        f"- Guidance scale in params: `{model.get('guidance_scale')}`",
        "",
        "## Current Controls",
        "",
        f"- DPM solver present: `{controls['dpm_solver_sample_present']}`",
        f"- DPM solver steps: `{controls['dpm_solver_steps']}`",
        f"- DPM skip type: `{controls['dpm_skip_type']}`",
        f"- CAMP adapter disables guidance: `{camp['adapter_disables_decoder_guidance']}`",
        f"- CAMP adapter restores guidance: `{camp['adapter_restores_decoder_guidance']}`",
        f"- Contract logged: `{camp['selection_record_contract_logged']}`",
        "",
        "## Guidance Inventory",
        "",
        f"- Composer present: `{guidance['composer_present']}`",
        f"- Legacy wrapper present: `{guidance['legacy_wrapper_present']}`",
        f"- Anchor/prototype support: `{guidance['anchor_following_present'] and guidance['prototype_builder_present']}`",
        f"- Registered functions: `{len(guidance['registered_guidance_functions'])}`",
        "",
        "## Admissibility",
        "",
        f"- Current runner guidance disabled: `{admissibility['current_runner_guidance_disabled']}`",
        f"- Official guidance available: `{admissibility['official_guidance_available']}`",
        f"- Prototype support available: `{admissibility['prototype_support_available']}`",
        f"- Next gate: `{next_gate['decision']}`",
        "",
        "## Mathematical Boundary",
        "",
        analysis["convexity_boundary"],
        "",
        "## Gate Requirements",
        "",
    ]
    for requirement in next_gate["requirements"]:
        lines.append(f"- {requirement}")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
