from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.integrations.plan_diffusion_planner_candidate_outcome_label_pass import (
    build_plan,
    main,
)


def _comparison(*, seed: int = 1, advance_mode: str = "perfect") -> dict[str, object]:
    rows = []
    for route_name, route in (
        ("sample_a", "/assets/sample_a.pkl"),
        ("sample_b", "/assets/sample_b.pkl"),
    ):
        rows.append(
            {
                "variant": "v10_redstopfloor05",
                "run_key": f"{route}|{seed}|200|4|0.3|True|{advance_mode}",
                "route_name": route_name,
                "route": route,
                "seed": seed,
                "steps": 200,
                "max_npcs": 4,
                "spawn_probability": 0.3,
                "traffic_lights": True,
                "advance_mode": advance_mode,
            }
        )
    return {"baseline": "top1", "runs": rows}


def _plan(comparison: dict[str, object]) -> dict[str, object]:
    return build_plan(
        comparison,
        source_variant="v10_redstopfloor05",
        label_output_root=Path("/out/labels"),
        diffusion_repo=Path("/dp"),
        map_path="/map.osm",
        model_path=Path("/assets/diffusion_planner.pth"),
        model_args=Path("/assets/diffusion_planner.param.json"),
        config=Path("/dp/scenario_generation/configs/replay_default.json"),
        reward_config=Path("configs/integrations/dp_camp_reward_eval.json"),
        camp_atom_scales=Path("/assets/redstop/atom_scales_dp_static.json"),
        camp_static_weights=Path("/assets/redstop/offline_weights_dp_static.npy"),
    )


def test_label_pass_plan_builds_static_outcome_collection_command() -> None:
    report = _plan(_comparison())
    argv = report["command"]["argv"]

    assert report["summary"]["scenario_count"] == 2
    assert report["summary"]["source_variant"] == "v10_redstopfloor05"
    assert report["analysis"]["runs_dp"] is False
    assert "--camp_collect_closed_loop_outcomes" in argv
    assert argv[argv.index("--variants") + 1] == "static"
    assert "--skip_compare" in argv
    assert "--route" in argv
    assert "sample_a=/assets/sample_a.pkl" in argv
    assert "sample_b=/assets/sample_b.pkl" in argv
    assert argv[argv.index("--seeds") + 1] == "1"
    assert argv[argv.index("--traffic_light_modes") + 1] == "on"


def test_label_pass_plan_rejects_formal_seeds() -> None:
    with pytest.raises(ValueError, match="formal seeds"):
        _plan(_comparison(seed=11))


def test_label_pass_plan_rejects_nonperfect_tracking() -> None:
    with pytest.raises(ValueError, match="perfect tracking"):
        _plan(_comparison(advance_mode="mpc"))


def test_label_pass_plan_cli_writes_outputs(tmp_path, monkeypatch) -> None:
    comparison_path = tmp_path / "comparison.json"
    output_json = tmp_path / "plan.json"
    output_md = tmp_path / "plan.md"
    comparison_path.write_text(json.dumps(_comparison()), encoding="utf-8")
    monkeypatch.setattr(
        "sys.argv",
        [
            "plan_diffusion_planner_candidate_outcome_label_pass.py",
            "--comparison_json",
            str(comparison_path),
            "--source_variant",
            "v10_redstopfloor05",
            "--label_output_root",
            "/out/labels",
            "--diffusion_repo",
            "/dp",
            "--map_path",
            "/map.osm",
            "--model_path",
            "/assets/diffusion_planner.pth",
            "--model_args",
            "/assets/diffusion_planner.param.json",
            "--config",
            "/dp/scenario_generation/configs/replay_default.json",
            "--reward_config",
            "configs/integrations/dp_camp_reward_eval.json",
            "--camp_atom_scales",
            "/assets/redstop/atom_scales_dp_static.json",
            "--camp_static_weights",
            "/assets/redstop/offline_weights_dp_static.npy",
            "--output_json",
            str(output_json),
            "--output_md",
            str(output_md),
        ],
    )

    main()

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["summary"]["scenario_count"] == 2
    assert "--camp_collect_closed_loop_outcomes" in output_md.read_text(
        encoding="utf-8"
    )
