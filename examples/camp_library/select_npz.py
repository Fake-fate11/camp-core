"""Select one original candidate from a caller-supplied, decision-time DP tick.

No inference, training, data download, or output-file write is performed. Each
invocation is independent: previous-plan continuity is not synthesized.
"""

import argparse
import json
from pathlib import Path

import numpy as np

from camp_core import dp
from camp_core.integrations.diffusion_planner_tier4_npz import (
    load_native_observation,
    native_camp_tick,
)
from camp_core.integrations.diffusion_planner_v26_camp_reranker import (
    V26_DP_MASKED_TOKEN_TYPES,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--observation", required=True, type=Path)
    parser.add_argument("--pool", required=True, type=Path)
    parser.add_argument("--mode", choices=("fixed", "scene"), default="fixed")
    parser.add_argument("--map", dest="projected_map", type=Path)
    parser.add_argument("--ego-pose", type=float, nargs=3, metavar=("X_M", "Y_M", "YAW_RAD"))
    args = parser.parse_args()
    if args.projected_map is not None and args.ego_pose is None:
        parser.error("--map requires --ego-pose in that map's original coordinate frame")

    observation = load_native_observation(args.observation)
    with np.load(args.pool, allow_pickle=False) as pool:
        prediction = pool["prediction"].copy()
        tokens = pool["encoder_tokens"].copy() if args.mode == "scene" else None
        masks = (
            {name: pool["mask_" + name].copy() for name in V26_DP_MASKED_TOKEN_TYPES}
            if args.mode == "scene" else None
        )

    ego_x, ego_y, ego_yaw = args.ego_pose or (0.0, 0.0, 0.0)
    map_context = None
    if args.projected_map is not None:
        from camp_core.integrations.autoware_map import AutowareMap

        map_context = AutowareMap(args.projected_map).context(ego_x, ego_y, ego_yaw)

    selector = dp.load(args.bundle)
    tick = native_camp_tick(
        observation, prediction,
        identity={"example": "single_saved_tick", "observation": args.observation.name},
        encoder_tokens=tokens, token_masks=masks, map_context=map_context,
        ego_x=ego_x, ego_y=ego_y, ego_yaw=ego_yaw,
    )
    decision = selector.select(tick, mode=args.mode)
    np.testing.assert_array_equal(decision.selected_trajectory, prediction[decision.selected_row, 0])
    print(json.dumps({
        "mode": args.mode,
        "candidate_count": int(len(prediction)),
        "selected_row": int(decision.selected_row),
        "candidate_scores": decision.rerank.candidate_scores.tolist(),
        "endpoint_status": list(decision.rerank.status_pattern),
        "selected_candidate_unchanged": True,
    }, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
