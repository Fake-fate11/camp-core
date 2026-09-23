"""Call installed TIER IV planner_metrics for offline candidate evaluation."""
from __future__ import annotations

import numpy as np


def evaluate_official(candidates, source):
    import torch
    from planner_metrics.config import RewardConfig
    from planner_metrics.scene_format import future_to_4col
    from planner_metrics import subscores as pm
    from planner_metrics import pdms_navsim as nav
    from planner_metrics.temporal_stability import compute_mean_abs_jerk_batch, compute_curvature_rate_batch
    from planner_metrics.gt_lateral_deviation import evaluate_gt_lateral_deviation_with_details
    from planner_metrics.centerline import compute_centerline_distance_batch

    tensor = lambda a: torch.as_tensor(np.array(a, copy=True), dtype=torch.float32)
    ego = tensor(candidates)
    config = RewardConfig()
    metrics, definitions, missing = {}, {}, {}

    def add(name, values, unit, direction, function, scope="full trajectory"):
        if torch.is_tensor(values):
            values = values.detach().cpu().numpy()
        values = np.asarray(values)
        if values.shape != (len(ego),) or not np.isfinite(values).all():
            raise ValueError(f"Non-finite/wrong-shape official output: {name}")
        metrics[name] = values.tolist()
        definitions[name] = dict(unit=unit, direction=direction, function=function, scope=scope)

    add("official_mean_abs_xy_jerk", compute_mean_abs_jerk_batch(ego), "m/s^3", "lower",
        "planner_metrics.temporal_stability.compute_mean_abs_jerk_batch", "SG 11/poly3/deriv3; trim 5 poses per edge")
    smooth = pm.compute_smoothness_score_batch(ego, config)
    np.testing.assert_allclose(-smooth.numpy(), metrics["official_mean_abs_xy_jerk"], rtol=1e-6)
    add("official_curvature_rate_proxy", compute_curvature_rate_batch(ego), "1/(m*s)", "lower",
        "planner_metrics.temporal_stability.compute_curvature_rate_batch", "SG derivatives; trimmed edges; within-plan, not inter-plan consistency")
    poses = np.asarray(candidates, dtype=np.float64)
    states = nav.states_from_poses(poses, .1)
    times = np.arange(80) * .1
    comfortable = nav.ego_is_comfortable(states, times)
    comfort_names = ("long_acc", "lat_acc", "mag_jerk", "long_jerk", "yaw_acc", "yaw_rate")
    for j, name in enumerate(comfort_names):
        add("official_comfort_"+name+"_within_bound", comfortable[:, j], "boolean", "higher",
            "planner_metrics.pdms_navsim.ego_is_comfortable", "all 80 poses within the corresponding official bound")
    add("official_comfort_all_six", nav.comfort_score(poses, .1), "boolean", "higher",
        "planner_metrics.pdms_navsim.comfort_score")

    shape = source.get("ego_shape")
    data = {k: tensor(source[k]) for k in ("route_lanes", "lanes", "line_strings") if k in source}
    if shape is not None:
        es = tensor(shape)
        feasibility, _disabled_offroad = pm.compute_feasibility_score_batch(ego, es, data, config)
        add("official_acceleration_feasibility_penalty", feasibility, "score", "higher",
            "planner_metrics.subscores.compute_feasibility_score_batch", "offroad output is disabled in official source and is not reported")
        add("official_kinematic_feasible", pm.compute_kinematic_gate(ego, config, es), "boolean", "higher",
            "planner_metrics.subscores.compute_kinematic_gate")
        ls = source.get("line_strings")
        if ls is not None and np.any(np.asarray(ls)[..., 3] > .5):
            border = pm.compute_road_border_penalty(ego, es, data, config)
            add("official_no_border_crossing", border[0], "boolean", "higher",
                "planner_metrics.subscores.compute_road_border_penalty", "cropped road-border lines; 0.20 m proximity test, not full-map containment")
            add("official_min_border_distance", border[5][:, 1:].min(1).values, "m", "higher",
                "planner_metrics.subscores.compute_road_border_penalty", "80 ego-perimeter samples; t>=1; cropped border segments")
        else:
            missing["road_border"] = "no source-labelled road-border segments"
    else:
        missing["vehicle_geometry"] = "ego_shape absent"

    coverage = {}
    nf, past = source.get("neighbor_agents_future"), source.get("neighbor_agents_past")
    if nf is not None and past is not None and shape is not None:
        nf = future_to_4col(nf)
        valid = np.abs(nf[..., :2]).sum(-1) > 1e-6
        active = valid.any(1)
        dims = np.asarray(past)[active, -1, 6:8]
        coverage = dict(active_actor_slots=int(active.sum()), total_actor_slots=len(nf),
                        valid_ticks_per_active_actor=valid[active].sum(1).tolist(),
                        observed_actor_ticks=int(valid.sum()), active_actor_ticks=int(active.sum())*80,
                        complete_actor_slots=int(valid[active].all(1).sum()),
                        all_active_actors_observed_ticks=int(valid[active].all(0).sum()))
        if active.any() and np.isfinite(nf).all() and np.isfinite(dims).all() and (dims > 0).all():
            futures, sizes = tensor(nf[active]), tensor(dims)
            vm = torch.as_tensor(valid[active], dtype=torch.bool)
            scope = "recorded actor-tick subset only; missing actor futures are not evidence of safety"
            distances = pm.compute_ego_neighbor_signed_clearance(ego, es, futures, sizes, vm)
            observed_distances = distances.masked_fill(~vm[None], float("inf"))
            add("official_recorded_subset_min_signed_clearance", observed_distances.flatten(1).min(1).values,
                "m", "higher", "planner_metrics.subscores.compute_ego_neighbor_signed_clearance", scope)
            safety, steps = pm.compute_safety_score_batch(ego, es, futures, sizes, vm, config)
            add("official_recorded_subset_safety_score", safety, "score", "higher",
                "planner_metrics.subscores.compute_safety_score_batch", scope)
            add("official_recorded_subset_collision_detected", [s is not None for s in steps], "boolean", "lower",
                "planner_metrics.subscores.compute_safety_score_batch", scope)
            ttc = pm.compute_ttc_score_batch(ego, es, futures, sizes, vm)
            add("official_recorded_subset_ttc_safe_fraction", ttc["score"], "fraction", "higher",
                "planner_metrics.subscores.compute_ttc_score_batch", scope+"; 1-second lookahead along recorded poses")
            if not valid[active].all():
                missing["complete_8s_actual_future_safety"] = "some initially observed actors have truncated future records"
        else:
            missing["actual_future_safety"] = "no active future actors or unusable source shapes/values; no dimension substitution"
    else:
        missing["actual_future_safety"] = "needs neighbor_agents_future, neighbor_agents_past and ego_shape"

    gt = source.get("ego_agent_future")
    gt_ok = gt is not None and gt.shape[0] == 80 and np.isfinite(gt).all() and np.any(gt)
    if gt_ok:
        gt = future_to_4col(gt, zero_rows_are_padding=False)
        gt_data = {"ego_agent_future": tensor(gt)[None].expand(len(ego), -1, -1)}
        err = evaluate_gt_lateral_deviation_with_details(ego, gt_data, {"horizon_seconds": 8.0})
        for name, values in err.scores.items():
            add("official_gt_"+name, values, "m", "lower",
                "planner_metrics.gt_lateral_deviation.evaluate_gt_lateral_deviation_with_details",
                "nearest GT path segment; not time-matched ADE/FDE")
        # Explicit source-derived alignment outcomes, not advertised as planner_metrics functions.
        displacement = np.linalg.norm(poses[..., :2]-gt[None, ..., :2], axis=-1)
        add("source_derived_ADE_8s", displacement.mean(1), "m", "lower", "mean time-matched Euclidean XY error")
        add("source_derived_FDE_8s", displacement[:, -1], "m", "lower", "final time-matched Euclidean XY error")
    else:
        missing["gt_alignment"] = "no finite 80-pose ego future"

    goal = source.get("goal_pose")
    goal_distance = None if goal is None else float(np.linalg.norm(goal[:2]))
    if goal is not None and 1e-6 < np.abs(goal[:2]).sum() and goal_distance <= 100:
        progress_data, progress_target = {}, "source goal_pose (within 100 m)"
    elif goal is not None and gt_ok and (np.abs(gt[:, :2]).sum(-1) > .1).sum() >= 10:
        progress_data, progress_target = {"ego_agent_future": tensor(gt)}, "official built-in GT-endpoint branch: source goal absent or >100 m"
    else:
        progress_data, progress_target = None, None
        missing["official_goal_progress"] = "no applicable goal or recorded GT endpoint; do not label path-length branch as goal progress"
    if progress_data is not None:
        # The official endpoint branch is an offline metric, never a CAMP input.
        goal_tensor = tensor(goal)
        add("official_goal_progress", pm.compute_progress_score_batch(ego, goal_tensor, progress_data),
            "m", "higher", "planner_metrics.subscores.compute_progress_score_batch", progress_target+"; first predicted pose to final pose")
    if "route_lanes" in source and np.any(source["route_lanes"][..., :4]):
        distance = compute_centerline_distance_batch(ego, data)
        add("official_mean_route_centerline_distance", distance.mean(1), "m", "lower",
            "planner_metrics.centerline.compute_centerline_distance_batch; mean over poses")
    missing["traffic_signal_compliance"] = "no authoritative future signal timeline/regulatory association"
    missing["temporal_consistency"] = "independent frame: needs real consecutive timestamps, episode, ego world poses and previous executed plan"
    return dict(metrics=metrics, definitions=definitions, missing=missing, neighbor_coverage=coverage,
                goal_distance_m=goal_distance, progress_target=progress_target,
                implementation=str(pm.__file__), numpy_version=np.__version__, torch_version=torch.__version__)
