from __future__ import annotations

import json

import pytest

from scripts.integrations.audit_diffusion_planner_candidate_generation_controls import (
    analyze,
    render_markdown,
)


def _write(path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fake_dp_repo(tmp_path):
    repo = tmp_path / "Diffusion-Planner"
    _write(
        repo
        / "diffusion_planner"
        / "diffusion_planner"
        / "model"
        / "module"
        / "decoder.py",
        """
class Decoder:
    def __init__(self):
        self._guidance_fn = None
        self._guidance_scale = 0.5

    def _inference_x_start(self):
        guidance_type = "classifier" if self._guidance_fn is not None else "uncond"
        dpm_solver.sample(xT, steps=10, prefix_mask=mask, skip_type="logSNR")
        return guidance_type
""",
    )
    guidance = (
        repo
        / "diffusion_planner"
        / "diffusion_planner"
        / "model"
        / "guidance"
    )
    _write(guidance / "composer.py", "class GuidanceComposer: pass\n")
    _write(guidance / "guidance_wrapper.py", "class GuidanceWrapper: pass\n")
    _write(
        guidance / "anchor_following.py",
        """
@register
class AnchorFollowingGuidance:
    name = "anchor_following"
""",
    )
    _write(
        repo / "diffusion_planner" / "sampling" / "build_prototypes.py",
        "def main(): pass\n",
    )
    return repo


def _fake_camp_root(tmp_path):
    root = tmp_path / "camp_core-main"
    _write(
        root / "camp_core" / "camp_core" / "integrations" / "diffusion_planner.py",
        """
def generate_candidate_trajectories(noise_scale, deterministic_first, reference_blend_steps):
    latent = torch.randn(8, 321, 81, 4) * float(noise_scale)
    original_guidance = getattr(decoder, "_guidance_fn", None)
    decoder._guidance_fn = None
    try:
        pass
    finally:
        decoder._guidance_fn = original_guidance
""",
    )
    _write(
        root / "scripts" / "integrations" / "run_diffusion_planner_camp_replay.py",
        """
def _candidate_generation_contract(): pass
record = {"candidate_generation_contract": True}
""",
    )
    return root


def test_generation_controls_audit_reports_guidance_boundary(tmp_path) -> None:
    dp_repo = _fake_dp_repo(tmp_path)
    camp_root = _fake_camp_root(tmp_path)
    model_args = tmp_path / "diffusion_planner.param.json"
    model_args.write_text(
        json.dumps(
            {
                "diffusion_model_type": "x_start",
                "future_len": 80,
                "predicted_neighbor_num": 320,
                "guidance_scale": 0.5,
            }
        ),
        encoding="utf-8",
    )

    report = analyze(
        dp_repo,
        model_args_path=model_args,
        camp_root=camp_root,
        num_candidates=16,
        candidate_noise_scale=0.75,
    )

    assert report["analysis"]["training"] is False
    assert report["current_contract"]["latent_shape"] == [16, 321, 81, 4]
    assert report["current_contract"]["guidance_enabled"] is False
    assert report["decoder_controls"]["dpm_solver_steps"] == 10
    assert report["decoder_controls"]["dpm_skip_type"] == "logSNR"
    assert report["camp_controls"]["adapter_disables_decoder_guidance"]
    assert report["camp_controls"]["adapter_restores_decoder_guidance"]
    assert report["guidance_inventory"]["registered_guidance_functions"] == [
        {
            "module": "anchor_following.py",
            "class": "AnchorFollowingGuidance",
            "name": "anchor_following",
        }
    ]
    assert report["admissibility"]["current_runner_guidance_disabled"]
    assert report["admissibility"]["official_guidance_available"]
    assert report["admissibility"]["prototype_support_available"]
    assert report["next_gate"]["decision"] == (
        "predeclare_default_off_guidance_candidate_set_diagnostic"
    )

    markdown = render_markdown(report)
    assert "DP Candidate Generation Controls Audit" in markdown
    assert "predeclare_default_off_guidance_candidate_set_diagnostic" in markdown


def test_generation_controls_audit_validates_candidate_parameters(tmp_path) -> None:
    dp_repo = _fake_dp_repo(tmp_path)
    camp_root = _fake_camp_root(tmp_path)
    model_args = tmp_path / "diffusion_planner.param.json"
    model_args.write_text(
        json.dumps({"future_len": 80, "predicted_neighbor_num": 320}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="num_candidates"):
        analyze(dp_repo, model_args_path=model_args, camp_root=camp_root, num_candidates=0)

    with pytest.raises(ValueError, match="candidate_noise_scale"):
        analyze(
            dp_repo,
            model_args_path=model_args,
            camp_root=camp_root,
            candidate_noise_scale=-1.0,
        )
