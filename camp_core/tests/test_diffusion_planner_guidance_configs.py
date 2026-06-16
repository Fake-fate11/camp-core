from __future__ import annotations

import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GUIDANCE_CONFIG = (
    ROOT
    / "configs"
    / "integrations"
    / "dp_candidate_guidance_route_centerline_lane.json"
)


def test_route_centerline_lane_guidance_config_is_official_schema() -> None:
    payload = json.loads(GUIDANCE_CONFIG.read_text(encoding="utf-8"))

    assert set(payload) == {"global_scale", "functions"}
    assert math.isfinite(payload["global_scale"])
    assert 0.0 < payload["global_scale"] <= 0.5

    functions = payload["functions"]
    assert [fn["name"] for fn in functions] == [
        "route_centerline_following",
        "lane_keeping",
    ]
    for function in functions:
        assert set(function) == {"name", "enabled", "scale", "params"}
        assert function["enabled"] is True
        assert math.isfinite(function["scale"])
        assert function["scale"] > 0.0
        assert function["params"] == {}
