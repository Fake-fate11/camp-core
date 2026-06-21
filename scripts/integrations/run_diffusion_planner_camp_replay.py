#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = ROOT / "camp_core"
for path in (ROOT, PACKAGE_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from camp_core.integrations.diffusion_planner import (  # noqa: E402
    DP_SCENE_FEATURE_NAMES,
    CAMPSelectionResult,
    CAMPSelector,
    atom_schema_for_dimension,
    build_context_from_scene,
    compute_candidate_closed_loop_outcomes,
    compute_candidate_obstacle_clearance_diagnostics,
    compute_dp_prior_comfort_excess_costs,
    compute_dp_prior_deviation_costs,
    compute_lateral_comfort_shadow_costs,
    compute_perfect_tracker_command_diagnostics,
    compute_perfect_tracker_open_loop_rollout_diagnostics,
    compute_red_stopping_margin_costs,
    extract_dp_scene_features,
    generate_candidate_trajectories,
    install_lanelet2_projection_fallback,
    load_dp_camp_atom_scales,
    red_route_points_from_scene,
    select_perfect_tracker_command_dominating_candidate,
    summarize_replay_artifacts,
)
from camp_core.integrations.diffusion_planner_progress_support import (  # noqa: E402
    PROGRESS_SUPPORT_ATOM_NAMES,
    PROGRESS_SUPPORT_FIELD_NAMES,
    PROGRESS_SUPPORT_LATENCY_KEYS,
    PROGRESS_SUPPORT_LOGGING_SCHEMA_VERSION,
    build_progress_support_logging_payload,
)
from camp_core.integrations.diffusion_planner_lane_hard_violation_support import (  # noqa: E402
    LANE_HARD_VIOLATION_SUPPORT_ATOM_NAMES,
    LANE_HARD_VIOLATION_SUPPORT_FIELD_NAMES,
    LANE_HARD_VIOLATION_SUPPORT_LATENCY_KEYS,
    LANE_HARD_VIOLATION_SUPPORT_LOGGING_SCHEMA_VERSION,
    build_lane_hard_violation_support_logging_payload,
)
from camp_core.integrations.diffusion_planner_progress_lane_hard_context import (  # noqa: E402
    PROGRESS_LANE_HARD_CONTEXT_ATOM_NAMES,
    PROGRESS_LANE_HARD_CONTEXT_FIELD_NAMES,
    PROGRESS_LANE_HARD_CONTEXT_LATENCY_KEYS,
    PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION,
    PROGRESS_LANE_HARD_CONTEXT_RELAXED_STRICT_ATOM_NAMES,
    PROGRESS_LANE_HARD_CONTEXT_RELAXED_STRICT_ATOM_SCHEMA_VERSION,
    PROGRESS_LANE_HARD_CONTEXT_REVISED_ATOM_NAMES,
    PROGRESS_LANE_HARD_CONTEXT_REVISED_ATOM_SCHEMA_VERSION,
    build_progress_lane_hard_context_logging_payload,
)
from camp_core.integrations.diffusion_planner_turn_logit_payload import (  # noqa: E402
    TURN_LOGIT_PAYLOAD_ATOM_CANDIDATE_NAMES,
    TURN_LOGIT_PAYLOAD_FIELD_NAMES,
    TURN_LOGIT_PAYLOAD_LATENCY_KEYS,
    TURN_LOGIT_PAYLOAD_SCHEMA_VERSION,
    build_turn_logit_payload,
)
from camp_core.integrations.diffusion_planner_non_turn_logit_interaction_payload import (  # noqa: E402
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_ATOM_CANDIDATE_NAMES,
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_DIAGNOSTIC_FIELD_NAMES,
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_FIELD_NAMES,
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_LATENCY_KEYS,
    NON_TURN_LOGIT_INTERACTION_PAYLOAD_SCHEMA_VERSION,
    build_non_turn_logit_interaction_payload,
)
from camp_core.integrations.diffusion_planner_external_context_payload import (  # noqa: E402
    EXTERNAL_CONTEXT_PAYLOAD_ATOM_CANDIDATE_NAMES,
    EXTERNAL_CONTEXT_PAYLOAD_FIELD_NAMES,
    EXTERNAL_CONTEXT_PAYLOAD_LATENCY_KEYS,
    EXTERNAL_CONTEXT_PAYLOAD_SCHEMA_VERSION,
    build_external_context_payload,
)
from camp_core.integrations.diffusion_planner_temporal_consistency_payload import (  # noqa: E402
    TEMPORAL_CONSISTENCY_PAYLOAD_ATOM_CANDIDATE_NAMES,
    TEMPORAL_CONSISTENCY_PAYLOAD_FIELD_NAMES,
    TEMPORAL_CONSISTENCY_PAYLOAD_LATENCY_KEYS,
    TEMPORAL_CONSISTENCY_PAYLOAD_SCHEMA_VERSION,
    build_temporal_consistency_payload,
)
from camp_core.atoms.driver_atoms import (  # noqa: E402
    exact_centerline_slice_for_candidates,
)
from scripts.integrations.analyze_diffusion_planner_splice_recompute_gate import (  # noqa: E402
    build_splice_candidates,
    fixed_candidate_shadow_rule,
    reason_counts,
    reward_hard_feasibility,
    reward_metric_vector,
)


PERFECT_TRACKER_OPEN_LOOP_HORIZONS = (3, 5, 10)
TRAFFIC_LIGHT_HYBRID_POSTSELECTION_MODES = (
    "off",
    "step_h10_guard_005",
    "h3_h10_guard_005",
    "state_redroute_top1_red_or_proxy_jerk_floor_unconditional",
    "state_redroute_top1_red_or_proxy_jerk_floor_lateral_nonworse",
)
TRAFFIC_LIGHT_HYBRID_POSTSELECTION_BUDGETS = {
    "step_h10_guard_005": {
        "first_step_loss_m": 0.10,
        "dp_reward_progress_loss_m": 0.05,
        "h10_distance_loss_m": 0.05,
        "target_speed_loss_mps": 0.05,
    },
    "h3_h10_guard_005": {
        "h3_distance_loss_m": 0.10,
        "dp_reward_progress_loss_m": 0.05,
        "h10_distance_loss_m": 0.05,
        "target_speed_loss_mps": 0.05,
    },
    "state_redroute_top1_red_or_proxy_jerk_floor_unconditional": {},
    "state_redroute_top1_red_or_proxy_jerk_floor_lateral_nonworse": {
        "candidate0_horizon_lateral_cost_delta_max": 0.0,
    },
}
TRAFFIC_LIGHT_HYBRID_TOL = 1e-12
STATE_REDROUTE_TOP1_FLOOR_MODE = (
    "state_redroute_top1_red_or_proxy_jerk_floor_unconditional"
)
STATE_REDROUTE_TOP1_FLOOR_LATERAL_NONWORSE_MODE = (
    "state_redroute_top1_red_or_proxy_jerk_floor_lateral_nonworse"
)
STATE_REDROUTE_TOP1_FLOOR_MODES = (
    STATE_REDROUTE_TOP1_FLOOR_MODE,
    STATE_REDROUTE_TOP1_FLOOR_LATERAL_NONWORSE_MODE,
)
OBSERVABLE_STATE_LOGGING_SCHEMA_VERSION = "dp_camp_observable_state_logging_v1"
OBSERVABLE_STATE_LATENCY_KEYS = (
    "latency_ms_observable_state_route_topology",
    "latency_ms_observable_state_traffic_light_relation",
    "latency_ms_observable_state_route_turn",
    "latency_ms_observable_state_neighbor_clearance",
)
OBSERVABLE_STATE_FIELDS = (
    "candidate_route_segment_index",
    "candidate_route_projection_s_m",
    "candidate_route_lateral_error_m",
    "candidate_red_stopline_distance_m",
    "candidate_red_heading_alignment",
    "candidate_route_heading_change_rad",
    "route_curvature_context_abs",
    "candidate_min_obstacle_clearance_lower_bound_m",
    "candidate_obstacle_slot_count",
)
RED_ROUTE_VECTOR_LOGGING_SCHEMA_VERSION = "dp_camp_red_route_vector_logging_v1"
RED_ROUTE_VECTOR_LATENCY_KEYS = ("latency_ms_red_route_vector_logging",)
RED_ROUTE_VECTOR_FIELDS = (
    "red_route_points_ego_xy_dir",
    "candidate_red_selected_route_point_index",
    "candidate_red_heading_vector_xy",
    "candidate_red_vector_to_selected_point_xy",
    "candidate_red_alignment_recomputed_current",
    "candidate_red_alignment_recomputed_reverse",
)
def _parse_step_list(value: str) -> tuple[int, ...]:
    steps = tuple(int(part.strip()) for part in value.split(",") if part.strip())
    if not steps:
        raise argparse.ArgumentTypeError("step list must not be empty")
    if any(step < 0 for step in steps):
        raise argparse.ArgumentTypeError("snapshot steps must be nonnegative")
    if len(set(steps)) != len(steps):
        raise argparse.ArgumentTypeError("snapshot steps must be unique")
    return steps


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run tier4/Diffusion-Planner route replay with CAMP selecting "
            "one ego trajectory from a stochastic candidate pool."
        )
    )
    parser.add_argument("--diffusion_repo", type=Path, required=True)
    parser.add_argument("--map_path", type=str, default=None)
    parser.add_argument("--route", type=Path, required=True)
    parser.add_argument("--model_path", type=Path, required=True)
    parser.add_argument(
        "--model_args",
        type=Path,
        default=None,
        help=(
            "Optional Diffusion Planner parameter JSON. Use this for official "
            "artifacts such as diffusion_planner.param.json; otherwise the "
            "upstream loader expects args.json next to the checkpoint."
        ),
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output_dir", type=Path, required=True)
    parser.add_argument("--device", type=str, default="cuda")
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--max_npcs", type=int, default=None)
    parser.add_argument("--spawn_probability", type=float, default=None)
    parser.add_argument(
        "--advance_mode",
        choices=("config", "perfect", "mpc", "teleport"),
        default="config",
        help="Override SpawnConfig.advance_mode for an auditable tracker choice.",
    )
    parser.add_argument(
        "--traffic_lights",
        choices=("config", "on", "off"),
        default="config",
        help="Override SpawnConfig.enable_traffic_lights for matched experiments.",
    )
    parser.add_argument(
        "--reward_config",
        type=Path,
        default=None,
        help=(
            "Optional full GRPO/reward JSON. When provided, the runner calls "
            "the upstream replay reward scorer in memory without dumping NPZs."
        ),
    )

    weights = parser.add_mutually_exclusive_group(required=False)
    weights.add_argument(
        "--camp_checkpoint",
        type=Path,
        help="CAMP-Select .pt checkpoint containing offline_weights.",
    )
    weights.add_argument(
        "--camp_static_weights",
        type=Path,
        help="Standalone offline_weights.npy.",
    )
    parser.add_argument("--camp_atom_scales", type=Path, default=None)
    parser.add_argument("--camp_fallback_atom_scales", type=Path, default=None)
    parser.add_argument("--camp_fallback_static_weights", type=Path, default=None)
    parser.add_argument(
        "--camp_selector_mode",
        choices=("top1", "uniform", "static", "linear"),
        default="static",
        help=(
            "top1 runs upstream Diffusion Planner unchanged; uniform generates "
            "K candidates and scores CAMP atoms with equal weights; static uses "
            "offline_weights; linear uses Theta from --camp_checkpoint and "
            "per-step Diffusion Planner scene features."
        ),
    )
    parser.add_argument(
        "--camp_fallback_mode",
        choices=("uniform", "learned", "top1"),
        default="uniform",
        help=(
            "Fallback policy when all candidates are infeasible. uniform keeps "
            "the legacy average-atom fallback; learned reuses selector scores; "
            "top1 preserves the upstream DP candidate0."
        ),
    )
    parser.add_argument("--camp_atom_clip", type=float, default=10.0)
    parser.add_argument("--camp_safety_radius", type=float, default=2.0)
    parser.add_argument("--camp_clearance_margin", type=float, default=1.0)
    parser.add_argument("--camp_lane_corridor_buffer", type=float, default=1.0)
    parser.add_argument(
        "--camp_feasibility_source",
        choices=("context", "dp_reward"),
        default="context",
        help=(
            "Use legacy CAMP route/speed gates or authoritative Diffusion Planner "
            "candidate reward gates before CAMP scoring."
        ),
    )
    parser.add_argument(
        "--camp_min_progress_ratio",
        type=float,
        default=0.8,
        help=(
            "For dp_reward feasibility, retain safe candidates whose progress is "
            "at least this fraction of the best safe candidate."
        ),
    )
    parser.add_argument(
        "--camp_min_candidate0_progress_ratio",
        type=float,
        default=None,
        help=(
            "For dp_reward feasibility, optionally require each safe candidate "
            "to retain at least this fraction of candidate 0 progress. This is "
            "a candidate0-relative deployment guard and does not affect CAMP "
            "atom scores or weights."
        ),
    )
    parser.add_argument(
        "--camp_min_candidate0_route_progress_ratio",
        type=float,
        default=None,
        help=(
            "For candidate selection, optionally require each candidate to "
            "retain at least this fraction of candidate 0 route-centerline "
            "progress over the current horizon. This guard is computed before "
            "CAMP scoring and does not affect atom scores or weights."
        ),
    )
    parser.add_argument(
        "--camp_shadow_route_progress",
        action="store_true",
        help=(
            "Compute and log candidate route-centerline progress without "
            "changing feasibility, scores, or selection. This is a shadow-only "
            "diagnostic for offline CAMP visibility audits."
        ),
    )
    parser.add_argument(
        "--camp_shadow_obstacle_clearance",
        action="store_true",
        help=(
            "Compute and log current-tick candidate obstacle-clearance hinge "
            "diagnostics without changing feasibility, scores, or selection. "
            "This is a shadow-only diagnostic for offline CAMP visibility audits."
        ),
    )
    parser.add_argument(
        "--camp_shadow_obstacle_clearance_exact_obb",
        action="store_true",
        help=(
            "Also compute near-threshold exact OBB clearance diagnostics for "
            "--camp_shadow_obstacle_clearance. Disabled by default because the "
            "online-eligible clearance hinges use the conservative lower bound."
        ),
    )
    parser.add_argument(
        "--camp_min_candidate0_step_reach_ratio",
        type=float,
        default=None,
        help=(
            "For perfect-tracking replay, optionally require each candidate's "
            "first reference point to be at least this fraction of candidate "
            "0 reach. This directly preserves the target speed used by the "
            "perfect tracker and does not affect CAMP atom scores or weights."
        ),
    )
    parser.add_argument(
        "--camp_candidate0_step_reach_preserve_feasible",
        action="store_true",
        help=(
            "When --camp_min_candidate0_step_reach_ratio is enabled, relax the "
            "step-reach guard for a tick if applying it would remove every "
            "candidate that was feasible before the guard. This keeps the guard "
            "from creating new all-infeasible fallback ticks and does not affect "
            "CAMP atom scores or weights."
        ),
    )
    parser.add_argument(
        "--camp_lexicographic_progress_epsilon_m",
        type=float,
        default=None,
        help=(
            "Enable a nonempty finite-candidate preselection that first keeps "
            "candidates within this many meters of the best feasible DP progress."
        ),
    )
    parser.add_argument(
        "--camp_lexicographic_red_epsilon",
        type=float,
        default=0.0,
        help="Planned-red cost tolerance for lexicographic preselection.",
    )
    parser.add_argument(
        "--camp_lexicographic_jerk_epsilon",
        type=float,
        default=0.0,
        help="DP-prior jerk-excess tolerance for lexicographic preselection.",
    )
    parser.add_argument(
        "--camp_lexicographic_lateral_epsilon",
        type=float,
        default=0.0,
        help="Horizon lateral-acceleration tolerance for lexicographic preselection.",
    )
    parser.add_argument(
        "--camp_perfect_tracker_command_postselection",
        action="store_true",
        help=(
            "After the normal CAMP selection, choose a base-feasible candidate "
            "only when it preserves target speed, DP progress, and planned-red "
            "cost while strictly improving PerfectTracker command comfort."
        ),
    )
    parser.add_argument(
        "--camp_traffic_light_hybrid_postselection",
        choices=TRAFFIC_LIGHT_HYBRID_POSTSELECTION_MODES,
        default="off",
        help=(
            "Default-off traffic-light-only finite-candidate postselection. "
            "Budgeted modes mirror the accepted offline certificate screens "
            "and require base feasibility, no worse red costs, strict proxy "
            "comfort improvement, and bounded progress/target-speed loss. "
            "The state_redroute Top-1 floor mode mirrors the offline "
            "state-gated jerk diagnostic and may return candidate0 without "
            "requiring candidate0 base feasibility."
        ),
    )
    parser.add_argument(
        "--camp_underprogress_relaxation",
        action="store_true",
        help=(
            "Default-off safety relaxation for red-light approach states. "
            "Only candidates blocked solely by dp_underprogress can be "
            "admitted, and hard feasibility reasons remain hard."
        ),
    )
    parser.add_argument(
        "--camp_underprogress_progress_loss_budget_m",
        type=float,
        default=1.5,
        help="Maximum DP progress loss for --camp_underprogress_relaxation.",
    )
    parser.add_argument(
        "--camp_underprogress_h3_distance_loss_budget_m",
        type=float,
        default=0.1,
        help="Maximum H3 PerfectTracker distance loss for underprogress relaxation.",
    )
    parser.add_argument(
        "--camp_underprogress_lateral_limit_mps2",
        type=float,
        default=2.0,
        help="Absolute H3 max lateral acceleration limit for underprogress relaxation.",
    )
    parser.add_argument(
        "--camp_reward_horizon_steps",
        type=int,
        default=30,
        help=(
            "Near-term trajectory steps used for DP candidate reward gates. "
            "Full selected trajectories are still evaluated separately."
        ),
    )
    parser.add_argument(
        "--camp_collect_closed_loop_outcomes",
        action="store_true",
        help=(
            "Log short-horizon candidate outcome labels computed from perfect "
            "tracking, predicted NPC futures, route progress, red lights, and "
            "comfort. Used for v5 closed_loop_outcome training."
        ),
    )
    parser.add_argument("--camp_outcome_horizon_steps", type=int, default=30)
    parser.add_argument("--camp_outcome_progress_weight", type=float, default=1.0)
    parser.add_argument("--camp_outcome_collision_penalty", type=float, default=100.0)
    parser.add_argument("--camp_outcome_near_miss_penalty", type=float, default=10.0)
    parser.add_argument("--camp_outcome_lane_penalty", type=float, default=20.0)
    parser.add_argument("--camp_outcome_red_light_penalty", type=float, default=30.0)
    parser.add_argument("--camp_outcome_jerk_penalty", type=float, default=0.25)
    parser.add_argument(
        "--camp_outcome_lateral_acceleration_penalty",
        type=float,
        default=1.0,
    )
    parser.add_argument("--num_candidates", type=int, default=8)
    parser.add_argument("--candidate_noise_scale", type=float, default=1.0)
    parser.add_argument(
        "--candidate_noise_strategy",
        choices=("iid", "antithetic"),
        default="iid",
        help=(
            "Default iid keeps historical latent sampling. Antithetic pairs "
            "stochastic latents as +z/-z in the same batched forward pass and "
            "changes only the finite candidate set."
        ),
    )
    parser.add_argument(
        "--candidate_reference_blend_steps",
        type=int,
        default=None,
        help=(
            "Blend stochastic candidates from candidate 0 at t=0 to their "
            "original trajectories after this many fixed steps."
        ),
    )
    parser.add_argument(
        "--candidate_guidance_config",
        type=Path,
        default=None,
        help=(
            "Default-off diagnostic: install official Diffusion Planner "
            "GuidanceComposer for candidate generation. This changes only the "
            "finite candidate set and must not be used for formal seeds before "
            "passing the predeclared gate."
        ),
    )
    parser.add_argument(
        "--candidate_guidance_scale",
        type=float,
        default=None,
        help=(
            "Optional decoder guidance scale override used only with "
            "--candidate_guidance_config."
        ),
    )
    parser.add_argument(
        "--camp_microbenchmark_snapshot_dir",
        type=Path,
        default=None,
        help=(
            "Default-off diagnostic export of current-tick DP/CAMP inputs. "
            "Snapshot runs are not latency evidence."
        ),
    )
    parser.add_argument(
        "--camp_microbenchmark_snapshot_steps",
        type=_parse_step_list,
        default=(10, 20, 30, 39),
        help="Comma-separated completed selection steps to export.",
    )
    parser.add_argument(
        "--camp_log_raw_candidate_prefix_steps",
        type=int,
        default=0,
        help=(
            "Default-off diagnostic logging of the raw Diffusion Planner "
            "candidate trajectory prefix before PerfectTracker postprocessing. "
            "This changes no selection behavior and is for offline audits only."
        ),
    )
    parser.add_argument(
        "--camp_observable_state_logging",
        action="store_true",
        help=(
            "Default-off no-leak logging of current-tick candidate route, "
            "traffic-light, turn-context, and neighbor-clearance descriptors. "
            "This records only fixed pre-outcome diagnostics and does not "
            "change feasibility, scores, or selection."
        ),
    )
    parser.add_argument(
        "--camp_observable_state_support_steps",
        type=int,
        default=10,
        help="Candidate prefix steps for observable route-support descriptors.",
    )
    parser.add_argument(
        "--camp_observable_state_traffic_light_steps",
        type=int,
        default=30,
        help="Candidate prefix steps for observable traffic-light descriptors.",
    )
    parser.add_argument(
        "--camp_observable_state_turn_steps",
        type=int,
        default=10,
        help="Candidate prefix steps for observable turn-context descriptors.",
    )
    parser.add_argument(
        "--camp_red_route_vector_logging",
        action="store_true",
        help=(
            "Default-off no-leak logging of current-tick red route point vectors "
            "and candidate heading vectors used to audit traffic-light alignment "
            "sign semantics. This does not change feasibility, scores, or selection."
        ),
    )
    parser.add_argument(
        "--camp_progress_support_logging",
        action="store_true",
        help=(
            "Default-off no-leak logging of current-tick candidate "
            "progress-support fields and fixed nonnegative atom coefficients. "
            "This records diagnostics only and does not change feasibility, "
            "scores, or selection."
        ),
    )
    parser.add_argument(
        "--camp_progress_support_steps",
        type=int,
        default=10,
        help="Candidate prefix steps for progress-support logging.",
    )
    parser.add_argument(
        "--camp_progress_support_dt_s",
        type=float,
        default=0.1,
        help="Time step used for progress-support speed-profile logging.",
    )
    parser.add_argument(
        "--camp_lane_hard_violation_support_logging",
        action="store_true",
        help=(
            "Default-off no-leak logging of current-tick candidate lane/"
            "hard-violation support fields and fixed nonnegative atom "
            "coefficients. This records diagnostics only and does not change "
            "feasibility, scores, or selection."
        ),
    )
    parser.add_argument(
        "--camp_lane_hard_violation_support_steps",
        type=int,
        default=10,
        help="Candidate prefix steps for lane/hard-violation support logging.",
    )
    parser.add_argument(
        "--camp_lane_hard_violation_support_dt_s",
        type=float,
        default=0.1,
        help="Time step used for lane/hard-violation lateral-rate logging.",
    )
    parser.add_argument(
        "--camp_lane_hard_violation_corridor_half_width_m",
        type=float,
        default=1.75,
        help=(
            "Explicit fallback route-lane corridor half width for default-off "
            "lane/hard-violation support logging."
        ),
    )
    parser.add_argument(
        "--camp_lane_hard_violation_lateral_rate_budget_mps",
        type=float,
        default=1.0,
        help=(
            "Nonnegative lateral-error-rate budget for lane/hard-violation "
            "support logging atoms."
        ),
    )
    parser.add_argument(
        "--camp_progress_lane_hard_context_logging",
        action="store_true",
        help=(
            "Default-off no-leak logging of current-tick progress+lane/hard "
            "context fields and fixed nonnegative atom coefficients. This "
            "records diagnostics only and does not change feasibility, scores, "
            "candidates, tracker execution, or selection."
        ),
    )
    parser.add_argument(
        "--camp_progress_lane_hard_context_steps",
        type=int,
        default=10,
        help="Candidate prefix steps for progress+lane/hard context logging.",
    )
    parser.add_argument(
        "--camp_progress_lane_hard_context_dt_s",
        type=float,
        default=0.1,
        help="Time step used for progress+lane/hard context kinematic logging.",
    )
    parser.add_argument(
        "--camp_progress_lane_hard_context_corridor_half_width_m",
        type=float,
        default=1.75,
        help=(
            "Explicit fallback route-lane corridor half width for default-off "
            "progress+lane/hard context logging."
        ),
    )
    parser.add_argument(
        "--camp_progress_lane_hard_context_corridor_safety_margin_m",
        type=float,
        default=0.25,
        help=(
            "Nonnegative corridor safety margin for progress+lane/hard context "
            "atom logging."
        ),
    )
    parser.add_argument(
        "--camp_turn_logit_payload_logging",
        action="store_true",
        help=(
            "Default-off no-leak logging of optional current-tick per-candidate "
            "turn-indicator logits returned by DP before CAMP selection. This "
            "records diagnostics only and does not change feasibility, scores, "
            "candidates, tracker execution, turn-indicator behavior, or "
            "selection."
        ),
    )
    parser.add_argument(
        "--camp_non_turn_logit_interaction_payload_logging",
        action="store_true",
        help=(
            "Default-off no-leak logging of current-tick non-turn-logit "
            "progress/comfort interaction fields. This records diagnostics "
            "only and does not change feasibility, scores, candidates, "
            "tracker execution, atom schema, CAMP weights, or selection."
        ),
    )
    parser.add_argument(
        "--camp_external_context_payload_logging",
        action="store_true",
        help=(
            "Default-off no-leak logging of current-tick traffic-signal and "
            "route speed-limit context payload fields. This records diagnostics "
            "only and does not change feasibility, scores, candidates, tracker "
            "execution, atom schema, CAMP weights, or selection."
        ),
    )
    parser.add_argument(
        "--camp_external_context_payload_steps",
        type=int,
        default=10,
        help="Candidate prefix steps for external-context payload logging.",
    )
    parser.add_argument(
        "--camp_external_context_payload_dt_s",
        type=float,
        default=0.1,
        help="Time step used for external-context payload speed/arrival logging.",
    )
    parser.add_argument(
        "--camp_temporal_consistency_payload_logging",
        action="store_true",
        help=(
            "Default-off no-leak logging of current-tick candidate RMS "
            "deviation from the previous tick selected planned trajectory. "
            "This records diagnostics only and does not change feasibility, "
            "scores, candidates, tracker execution, atom schema, CAMP weights, "
            "or selection."
        ),
    )
    parser.add_argument(
        "--camp_temporal_consistency_payload_steps",
        type=int,
        default=10,
        help="Candidate prefix steps for temporal-consistency payload logging.",
    )
    parser.add_argument(
        "--camp_temporal_consistency_payload_dt_s",
        type=float,
        default=0.1,
        help="Time step used for temporal-consistency payload logging.",
    )
    parser.add_argument(
        "--camp_temporal_consistency_payload_elapsed_steps",
        type=int,
        default=1,
        help=(
            "Planner samples to drop from the previous selected plan before "
            "temporal-consistency comparison."
        ),
    )
    parser.add_argument(
        "--camp_temporal_consistency_payload_min_overlap_steps",
        type=int,
        default=2,
        help="Minimum overlap steps required for temporal-consistency payload availability.",
    )
    parser.add_argument(
        "--camp_splice_shadow_rule",
        action="store_true",
        help=(
            "Default-off closed-loop shadow logging for the fixed-candidate "
            "stop-aware splice rule. This recomputes DP reward for transformed "
            "candidates and records a hypothetical choice without changing "
            "the selected trajectory."
        ),
    )
    parser.add_argument("--camp_splice_shadow_anchor_steps", type=int, default=10)
    parser.add_argument("--camp_splice_shadow_blend_steps", type=int, default=40)
    parser.add_argument(
        "--camp_splice_shadow_heading_mode",
        choices=("finite_difference", "donor_offset"),
        default="donor_offset",
    )
    parser.add_argument(
        "--camp_splice_shadow_progress_loss_budget_m",
        type=float,
        default=1.0,
    )
    parser.add_argument(
        "--camp_splice_shadow_smoothness_loss_budget",
        type=float,
        default=0.5,
    )
    parser.add_argument("--near_miss_threshold_m", type=float, default=2.0)
    return parser.parse_args()


def _validate_args(args: argparse.Namespace) -> None:
    if args.camp_selector_mode != "top1" and args.camp_atom_scales is None:
        raise ValueError(
            "--camp_atom_scales is required for uniform/static/linear CAMP modes."
        )
    if args.camp_selector_mode == "static" and (
        args.camp_checkpoint is None and args.camp_static_weights is None
    ):
        raise ValueError(
            "static CAMP selection requires --camp_checkpoint or "
            "--camp_static_weights."
        )
    if args.camp_selector_mode == "linear" and args.camp_checkpoint is None:
        raise ValueError("linear CAMP selection requires --camp_checkpoint.")
    if (args.camp_fallback_atom_scales is None) != (
        args.camp_fallback_static_weights is None
    ):
        raise ValueError(
            "--camp_fallback_atom_scales and --camp_fallback_static_weights "
            "must be provided together."
        )
    if (
        args.camp_fallback_static_weights is not None
        and args.camp_fallback_mode != "learned"
    ):
        raise ValueError(
            "Dedicated fallback artifacts require --camp_fallback_mode learned."
        )
    if args.camp_selector_mode != "top1" and args.num_candidates < 2:
        raise ValueError("--num_candidates must be >= 2 for CAMP candidate selection.")
    if args.candidate_noise_scale <= 0:
        raise ValueError("--candidate_noise_scale must be > 0.")
    if (
        args.candidate_reference_blend_steps is not None
        and args.candidate_reference_blend_steps < 1
    ):
        raise ValueError("--candidate_reference_blend_steps must be >= 1.")
    if args.candidate_guidance_scale is not None:
        if args.candidate_guidance_config is None:
            raise ValueError(
                "--candidate_guidance_scale requires --candidate_guidance_config."
            )
        if not np.isfinite(args.candidate_guidance_scale):
            raise ValueError("--candidate_guidance_scale must be finite.")
    if args.camp_lane_corridor_buffer < 0:
        raise ValueError("--camp_lane_corridor_buffer must be non-negative.")
    if not 0.0 <= args.camp_min_progress_ratio <= 1.0:
        raise ValueError("--camp_min_progress_ratio must be in [0, 1].")
    if args.camp_min_candidate0_progress_ratio is not None and not (
        0.0 <= args.camp_min_candidate0_progress_ratio <= 1.0
    ):
        raise ValueError("--camp_min_candidate0_progress_ratio must be in [0, 1].")
    if args.camp_min_candidate0_route_progress_ratio is not None and not (
        0.0 <= args.camp_min_candidate0_route_progress_ratio <= 1.0
    ):
        raise ValueError(
            "--camp_min_candidate0_route_progress_ratio must be in [0, 1]."
        )
    if args.camp_min_candidate0_step_reach_ratio is not None and not (
        0.0 <= args.camp_min_candidate0_step_reach_ratio <= 1.0
    ):
        raise ValueError("--camp_min_candidate0_step_reach_ratio must be in [0, 1].")
    lexicographic_epsilons = (
        args.camp_lexicographic_progress_epsilon_m,
        args.camp_lexicographic_red_epsilon,
        args.camp_lexicographic_jerk_epsilon,
        args.camp_lexicographic_lateral_epsilon,
    )
    if any(
        value is not None and (not np.isfinite(value) or value < 0.0)
        for value in lexicographic_epsilons
    ):
        raise ValueError(
            "CAMP lexicographic epsilons must be finite and nonnegative."
        )
    if (
        args.camp_lexicographic_progress_epsilon_m is not None
        and args.camp_feasibility_source != "dp_reward"
    ):
        raise ValueError(
            "CAMP lexicographic preselection requires "
            "--camp_feasibility_source dp_reward."
        )
    if (
        args.camp_perfect_tracker_command_postselection
        and args.camp_feasibility_source != "dp_reward"
    ):
        raise ValueError(
            "PerfectTracker command postselection requires "
            "--camp_feasibility_source dp_reward."
        )
    traffic_light_hybrid_enabled = (
        args.camp_traffic_light_hybrid_postselection != "off"
    )
    if traffic_light_hybrid_enabled and args.camp_selector_mode == "top1":
        raise ValueError(
            "Traffic-light hybrid postselection requires a CAMP selector mode."
        )
    if traffic_light_hybrid_enabled and args.camp_feasibility_source != "dp_reward":
        raise ValueError(
            "Traffic-light hybrid postselection requires "
            "--camp_feasibility_source dp_reward."
        )
    if (
        traffic_light_hybrid_enabled
        and args.camp_lexicographic_progress_epsilon_m is not None
    ):
        raise ValueError(
            "Traffic-light hybrid postselection cannot be combined with "
            "lexicographic preselection in the same run."
        )
    if (
        traffic_light_hybrid_enabled
        and args.camp_perfect_tracker_command_postselection
    ):
        raise ValueError(
            "Traffic-light hybrid postselection cannot be combined with "
            "PerfectTracker command postselection in the same run."
        )
    underprogress_budgets = (
        args.camp_underprogress_progress_loss_budget_m,
        args.camp_underprogress_h3_distance_loss_budget_m,
        args.camp_underprogress_lateral_limit_mps2,
    )
    if any(not np.isfinite(value) or value < 0.0 for value in underprogress_budgets):
        raise ValueError(
            "CAMP underprogress relaxation budgets must be finite and nonnegative."
        )
    if (
        args.camp_underprogress_relaxation
        and args.camp_feasibility_source != "dp_reward"
    ):
        raise ValueError(
            "CAMP underprogress relaxation requires "
            "--camp_feasibility_source dp_reward."
        )
    if (
        args.camp_underprogress_relaxation
        and args.camp_lexicographic_progress_epsilon_m is not None
    ):
        raise ValueError(
            "CAMP underprogress relaxation cannot be combined with "
            "lexicographic preselection in the same run."
        )
    if (
        args.camp_underprogress_relaxation
        and args.camp_perfect_tracker_command_postselection
    ):
        raise ValueError(
            "CAMP underprogress relaxation cannot be combined with "
            "PerfectTracker command postselection in the same run."
        )
    if args.camp_underprogress_relaxation and traffic_light_hybrid_enabled:
        raise ValueError(
            "CAMP underprogress relaxation cannot be combined with "
            "traffic-light hybrid postselection in the same run."
        )
    if args.camp_reward_horizon_steps < 2:
        raise ValueError("--camp_reward_horizon_steps must be >= 2.")
    if args.camp_outcome_horizon_steps < 2:
        raise ValueError("--camp_outcome_horizon_steps must be >= 2.")
    if args.camp_feasibility_source == "dp_reward" and args.reward_config is None:
        raise ValueError(
            "--camp_feasibility_source dp_reward requires --reward_config."
        )
    if args.near_miss_threshold_m < 0:
        raise ValueError("--near_miss_threshold_m must be non-negative.")
    if args.camp_log_raw_candidate_prefix_steps < 0:
        raise ValueError("--camp_log_raw_candidate_prefix_steps must be non-negative.")
    observable_state_steps = (
        args.camp_observable_state_support_steps,
        args.camp_observable_state_traffic_light_steps,
        args.camp_observable_state_turn_steps,
    )
    if any(value < 2 for value in observable_state_steps):
        raise ValueError("CAMP observable-state logging horizons must be >= 2.")
    if args.camp_progress_support_steps < 2:
        raise ValueError("--camp_progress_support_steps must be >= 2.")
    if (
        not np.isfinite(args.camp_progress_support_dt_s)
        or args.camp_progress_support_dt_s <= 0.0
    ):
        raise ValueError("--camp_progress_support_dt_s must be finite and positive.")
    if args.camp_lane_hard_violation_support_steps < 2:
        raise ValueError("--camp_lane_hard_violation_support_steps must be >= 2.")
    if (
        not np.isfinite(args.camp_lane_hard_violation_support_dt_s)
        or args.camp_lane_hard_violation_support_dt_s <= 0.0
    ):
        raise ValueError(
            "--camp_lane_hard_violation_support_dt_s must be finite and positive."
        )
    if (
        not np.isfinite(args.camp_lane_hard_violation_corridor_half_width_m)
        or args.camp_lane_hard_violation_corridor_half_width_m <= 0.0
    ):
        raise ValueError(
            "--camp_lane_hard_violation_corridor_half_width_m must be finite and positive."
        )
    if (
        not np.isfinite(args.camp_lane_hard_violation_lateral_rate_budget_mps)
        or args.camp_lane_hard_violation_lateral_rate_budget_mps < 0.0
    ):
        raise ValueError(
            "--camp_lane_hard_violation_lateral_rate_budget_mps must be finite and nonnegative."
        )
    if args.camp_progress_lane_hard_context_steps < 2:
        raise ValueError("--camp_progress_lane_hard_context_steps must be >= 2.")
    if (
        not np.isfinite(args.camp_progress_lane_hard_context_dt_s)
        or args.camp_progress_lane_hard_context_dt_s <= 0.0
    ):
        raise ValueError(
            "--camp_progress_lane_hard_context_dt_s must be finite and positive."
        )
    if (
        not np.isfinite(args.camp_progress_lane_hard_context_corridor_half_width_m)
        or args.camp_progress_lane_hard_context_corridor_half_width_m <= 0.0
    ):
        raise ValueError(
            "--camp_progress_lane_hard_context_corridor_half_width_m must be finite and positive."
        )
    if (
        not np.isfinite(args.camp_progress_lane_hard_context_corridor_safety_margin_m)
        or args.camp_progress_lane_hard_context_corridor_safety_margin_m < 0.0
    ):
        raise ValueError(
            "--camp_progress_lane_hard_context_corridor_safety_margin_m must be finite and nonnegative."
        )
    if args.camp_external_context_payload_steps < 2:
        raise ValueError("--camp_external_context_payload_steps must be >= 2.")
    if (
        not np.isfinite(args.camp_external_context_payload_dt_s)
        or args.camp_external_context_payload_dt_s <= 0.0
    ):
        raise ValueError(
            "--camp_external_context_payload_dt_s must be finite and positive."
        )
    if args.camp_temporal_consistency_payload_steps < 2:
        raise ValueError("--camp_temporal_consistency_payload_steps must be >= 2.")
    if (
        not np.isfinite(args.camp_temporal_consistency_payload_dt_s)
        or args.camp_temporal_consistency_payload_dt_s <= 0.0
    ):
        raise ValueError(
            "--camp_temporal_consistency_payload_dt_s must be finite and positive."
        )
    if args.camp_temporal_consistency_payload_elapsed_steps < 0:
        raise ValueError(
            "--camp_temporal_consistency_payload_elapsed_steps must be nonnegative."
        )
    if args.camp_temporal_consistency_payload_min_overlap_steps < 2:
        raise ValueError(
            "--camp_temporal_consistency_payload_min_overlap_steps must be >= 2."
        )
    splice_shadow_budgets = (
        args.camp_splice_shadow_progress_loss_budget_m,
        args.camp_splice_shadow_smoothness_loss_budget,
    )
    if any(not np.isfinite(value) or value < 0.0 for value in splice_shadow_budgets):
        raise ValueError("CAMP splice shadow budgets must be finite and nonnegative.")
    if args.camp_splice_shadow_anchor_steps < 2:
        raise ValueError("--camp_splice_shadow_anchor_steps must be >= 2.")
    if args.camp_splice_shadow_blend_steps < 0:
        raise ValueError("--camp_splice_shadow_blend_steps must be nonnegative.")
    if args.camp_splice_shadow_rule and args.camp_selector_mode == "top1":
        raise ValueError("CAMP splice shadow rule requires a CAMP selector mode.")
    if args.camp_splice_shadow_rule and args.camp_feasibility_source != "dp_reward":
        raise ValueError(
            "CAMP splice shadow rule requires --camp_feasibility_source dp_reward."
        )
    if (
        args.camp_splice_shadow_rule
        and args.camp_lexicographic_progress_epsilon_m is not None
    ):
        raise ValueError(
            "CAMP splice shadow rule cannot be combined with lexicographic "
            "preselection in the same run."
        )
    if args.camp_splice_shadow_rule and args.camp_underprogress_relaxation:
        raise ValueError(
            "CAMP splice shadow rule cannot be combined with underprogress "
            "relaxation in the same run."
        )
    if (
        args.camp_splice_shadow_rule
        and args.camp_perfect_tracker_command_postselection
    ):
        raise ValueError(
            "CAMP splice shadow rule cannot be combined with PerfectTracker "
            "command postselection in the same run."
        )
    if args.camp_splice_shadow_rule and traffic_light_hybrid_enabled:
        raise ValueError(
            "CAMP splice shadow rule cannot be combined with traffic-light "
            "hybrid postselection in the same run."
        )
    if args.reward_config is not None and not args.reward_config.is_file():
        raise FileNotFoundError(f"Missing reward config: {args.reward_config}")
    if (
        args.camp_microbenchmark_snapshot_dir is not None
        and args.camp_selector_mode == "top1"
    ):
        raise ValueError(
            "CAMP microbenchmark snapshots require a CAMP selector mode."
        )
    if (
        args.steps is not None
        and args.camp_microbenchmark_snapshot_dir is not None
        and max(args.camp_microbenchmark_snapshot_steps) >= args.steps
    ):
        raise ValueError(
            "Every CAMP microbenchmark snapshot step must be smaller than "
            "--steps."
        )


def _build_selector(args: argparse.Namespace) -> CAMPSelector | None:
    if args.camp_selector_mode == "top1":
        return None
    if args.camp_selector_mode == "uniform":
        atom_scales = load_dp_camp_atom_scales(args.camp_atom_scales)
        fallback_atom_scales = (
            None
            if args.camp_fallback_atom_scales is None
            else load_dp_camp_atom_scales(args.camp_fallback_atom_scales)
        )
        fallback_static_weights = (
            None
            if args.camp_fallback_static_weights is None
            else np.load(args.camp_fallback_static_weights)
        )
        return CAMPSelector(
            atom_scales,
            static_weights=np.ones_like(atom_scales, dtype=np.float64),
            mode="static",
            fallback_mode=args.camp_fallback_mode,
            fallback_atom_scales=fallback_atom_scales,
            fallback_static_weights=fallback_static_weights,
            atom_clip=args.camp_atom_clip,
        )
    return CAMPSelector.from_files(
        atom_scales_path=args.camp_atom_scales,
        checkpoint_path=args.camp_checkpoint,
        static_weights_path=args.camp_static_weights,
        fallback_atom_scales_path=args.camp_fallback_atom_scales,
        fallback_static_weights_path=args.camp_fallback_static_weights,
        mode=args.camp_selector_mode,
        fallback_mode=args.camp_fallback_mode,
        atom_clip=args.camp_atom_clip,
    )


def _install_diffusion_repo(diffusion_repo: Path) -> None:
    repo = diffusion_repo.resolve()
    required = [
        repo / "scenario_generation" / "replay.py",
        repo / "diffusion_planner" / "diffusion_planner" / "model",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(
            f"{repo} is not a tier4/Diffusion-Planner checkout; missing: {missing}"
        )
    for path in (repo, repo / "diffusion_planner"):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)


def _load_model(model_path: Path, model_args_path: Path | None, device: str):
    if model_args_path is None:
        import scenario_generation.replay as replay

        return replay.load_model(model_path, device)

    import torch
    from diffusion_planner.model.diffusion_planner import Diffusion_Planner
    from diffusion_planner.utils.config import Config

    args = Config(str(model_args_path))
    model = Diffusion_Planner(args)
    checkpoint = torch.load(str(model_path), map_location=device, weights_only=False)
    state = checkpoint.get("model", checkpoint)
    state = {key.replace("module.", ""): value for key, value in state.items()}
    model.load_state_dict(state)
    model.to(device)
    model.eval()
    return model, args


def _configure_candidate_guidance(
    model: Any,
    *,
    guidance_config_path: Path | None,
    guidance_scale: float | None,
) -> dict[str, Any]:
    if guidance_config_path is None:
        return {
            "enabled": False,
            "policy": "disabled_for_camp_candidate_generation",
            "config_path": None,
            "config_sha256": None,
            "functions": [],
            "guidance_scale": None,
        }

    if not guidance_config_path.is_file():
        raise FileNotFoundError(
            f"candidate guidance config not found: {guidance_config_path}"
        )

    from diffusion_planner.model.guidance.composer import GuidanceComposer
    from diffusion_planner.model.guidance.config import GuidanceSetConfig

    set_config = GuidanceSetConfig.from_file(str(guidance_config_path))
    functions = []
    for fn in set_config.functions:
        functions.append(
            {
                "name": str(fn.name),
                "enabled": bool(fn.enabled),
                "scale": float(fn.scale),
                "params": dict(fn.params),
            }
        )
    active = [fn for fn in functions if fn["enabled"]]
    if not active:
        raise ValueError(
            "--candidate_guidance_config must contain at least one enabled "
            "guidance function."
        )

    model.decoder._guidance_fn = GuidanceComposer(set_config)
    configured_global_scale = float(getattr(set_config, "global_scale", 0.0))
    if not np.isfinite(configured_global_scale):
        raise ValueError("--candidate_guidance_config global_scale must be finite.")
    if guidance_scale is not None:
        if not np.isfinite(guidance_scale):
            raise ValueError("--candidate_guidance_scale must be finite.")
        model.decoder._guidance_scale = float(guidance_scale)
        guidance_scale_source = "cli_override"
    else:
        model.decoder._guidance_scale = configured_global_scale
        guidance_scale_source = "config_global_scale"
    effective_scale = float(getattr(model.decoder, "_guidance_scale"))
    if not np.isfinite(effective_scale):
        raise ValueError("effective candidate guidance scale must be finite.")
    return {
        "enabled": True,
        "policy": "preserve_official_dp_guidance_for_candidate_generation",
        "config_path": str(guidance_config_path),
        "config_sha256": _sha256_file(guidance_config_path),
        "functions": functions,
        "active_function_names": [fn["name"] for fn in active],
        "guidance_scale": effective_scale,
        "guidance_scale_source": guidance_scale_source,
        "global_scale": configured_global_scale,
        "composer": "diffusion_planner.model.guidance.composer.GuidanceComposer",
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ego_frame_xy(world_xy: np.ndarray, ego_xy: np.ndarray, ego_heading: float) -> np.ndarray:
    relative = np.asarray(world_xy, dtype=np.float64) - ego_xy.reshape(1, 2)
    c = math.cos(ego_heading)
    s = math.sin(ego_heading)
    rotation = np.array([[c, s], [-s, c]], dtype=np.float64)
    return relative @ rotation.T


def _candidate_obstacles(
    scene: Any,
    ego_agent_id: str,
    neighbor_predictions: np.ndarray,
    is_static_npc,
) -> np.ndarray:
    """Match tensor_converter's distance-sorted neighbor slot order.

    Returns ``[K, M, T, 6]`` as x, y, heading, length, width, wheelbase in
    the ego frame. Older CAMP code only consumed x/y; the extra columns enable
    oriented bounding-box collision checks without changing DP internals.
    """
    ego = scene.get_agent(ego_agent_id)
    ego_xy = np.asarray(ego.current_position, dtype=np.float64)
    ego_heading = float(ego.current_heading)

    neighbors = [agent for agent in scene.agents if agent.id != ego_agent_id]
    neighbors.sort(
        key=lambda agent: float(
            np.linalg.norm(np.asarray(agent.current_position) - ego_xy)
        )
    )

    count = min(len(neighbors), neighbor_predictions.shape[1])
    obstacles = np.zeros(
        (neighbor_predictions.shape[0], count, neighbor_predictions.shape[2], 6),
        dtype=np.float64,
    )
    obstacles[:, :, :, :2] = neighbor_predictions[:, :count, :, :2]
    if neighbor_predictions.shape[-1] >= 4:
        obstacles[:, :, :, 2] = np.arctan2(
            neighbor_predictions[:, :count, :, 3],
            neighbor_predictions[:, :count, :, 2],
        )
    for neighbor_idx, agent in enumerate(neighbors[:count]):
        obstacles[:, neighbor_idx, :, 3] = float(getattr(agent, "length", 4.5))
        obstacles[:, neighbor_idx, :, 4] = float(getattr(agent, "width", 1.9))
        obstacles[:, neighbor_idx, :, 5] = float(
            getattr(agent, "wheelbase", 0.65 * getattr(agent, "length", 4.5))
        )
        if not is_static_npc(agent.id):
            continue
        static_xy = _ego_frame_xy(
            np.asarray(agent.current_position, dtype=np.float64).reshape(1, 2),
            ego_xy,
            ego_heading,
        )[0]
        obstacles[:, neighbor_idx, :, 0] = static_xy[0]
        obstacles[:, neighbor_idx, :, 1] = static_xy[1]
        obstacles[:, neighbor_idx, :, 2] = (
            float(agent.current_heading) - ego_heading
        )
    return obstacles


def _route_centerline_world(builder: Any, route: Any) -> np.ndarray:
    points: list[np.ndarray] = []
    for lanelet_id in route.route_lanelet_ids or []:
        cached = builder._cache.get(lanelet_id)
        if cached is None:
            continue
        centerline = np.asarray(cached.raw_centerline, dtype=np.float64)[:, :2]
        if centerline.shape[0] < 2:
            continue
        if points and np.linalg.norm(points[-1][-1] - centerline[0]) < 1e-3:
            centerline = centerline[1:]
        if centerline.size:
            points.append(centerline)
    if not points:
        return np.zeros((0, 2), dtype=np.float64)
    return np.concatenate(points, axis=0)


def _candidate_route_progress(
    candidates: np.ndarray,
    route_centerline: np.ndarray,
) -> np.ndarray | None:
    centerline = np.asarray(route_centerline, dtype=np.float64)
    if centerline.ndim != 2 or centerline.shape[0] < 2 or centerline.shape[1] < 2:
        return None
    candidate_xy = np.asarray(candidates, dtype=np.float64)[..., :2]
    if candidate_xy.ndim != 3 or candidate_xy.shape[1] < 1:
        return None

    starts = centerline[:-1, :2]
    ends = centerline[1:, :2]
    segments = ends - starts
    lengths = np.linalg.norm(segments, axis=1)
    valid = lengths > 1e-6
    if not np.any(valid):
        return None
    valid_segment_indices = np.flatnonzero(valid)
    starts = starts[valid]
    segments = segments[valid]
    lengths = lengths[valid]
    cumulative = np.concatenate([[0.0], np.cumsum(lengths)])
    cumulative_starts = cumulative[:-1]

    sliced, slice_stats = exact_centerline_slice_for_candidates(
        centerline[:, :2],
        candidate_xy,
    )
    if not bool(slice_stats.get("fail_closed", True)):
        segment_start = int(slice_stats["segment_start"])
        segment_end = int(slice_stats["segment_end"])
        slice_mask = (
            (valid_segment_indices >= segment_start)
            & (valid_segment_indices <= segment_end)
        )
        if np.any(slice_mask):
            starts = starts[slice_mask]
            segments = segments[slice_mask]
            lengths = lengths[slice_mask]
            cumulative_starts = cumulative_starts[slice_mask]

    flat = candidate_xy.reshape(-1, 2)
    point_arcs = np.zeros(flat.shape[0], dtype=np.float64)
    for point_idx, point in enumerate(flat):
        rel = point.reshape(1, 2) - starts
        t = np.sum(rel * segments, axis=1) / np.maximum(lengths * lengths, 1e-12)
        t = np.clip(t, 0.0, 1.0)
        projections = starts + t.reshape(-1, 1) * segments
        distances = np.linalg.norm(projections - point.reshape(1, 2), axis=1)
        best = int(np.argmin(distances))
        point_arcs[point_idx] = (
            cumulative_starts[best] + t[best] * lengths[best]
        )
    return np.max(point_arcs.reshape(candidate_xy.shape[:2]), axis=1)


def _route_progress_for_points(
    points_xy: np.ndarray,
    route_centerline: np.ndarray,
) -> np.ndarray | None:
    points = np.asarray(points_xy, dtype=np.float64)
    centerline = np.asarray(route_centerline, dtype=np.float64)
    if points.ndim != 2 or points.shape[0] < 1 or points.shape[1] < 2:
        return None
    if centerline.ndim != 2 or centerline.shape[0] < 2 or centerline.shape[1] < 2:
        return None
    if not np.all(np.isfinite(points[:, :2])) or not np.all(
        np.isfinite(centerline[:, :2])
    ):
        return None

    starts = centerline[:-1, :2]
    ends = centerline[1:, :2]
    segments = ends - starts
    lengths = np.linalg.norm(segments, axis=1)
    valid = lengths > 1e-6
    if not np.any(valid):
        return None
    starts = starts[valid]
    segments = segments[valid]
    lengths = lengths[valid]
    cumulative = np.concatenate([[0.0], np.cumsum(lengths)])
    cumulative_starts = cumulative[:-1]

    progress = np.zeros(points.shape[0], dtype=np.float64)
    for point_idx, point in enumerate(points[:, :2]):
        rel = point.reshape(1, 2) - starts
        t = np.sum(rel * segments, axis=1) / np.maximum(lengths * lengths, 1e-12)
        t = np.clip(t, 0.0, 1.0)
        projected = starts + t.reshape(-1, 1) * segments
        distances = np.linalg.norm(projected - point.reshape(1, 2), axis=1)
        best = int(np.argmin(distances))
        progress[point_idx] = cumulative_starts[best] + t[best] * lengths[best]
    return progress


def build_current_tick_signal_context(
    *,
    red_route_points_ego: np.ndarray | None,
    route_centerline_ego: np.ndarray | None,
    traffic_lights_enabled: bool,
) -> dict[str, Any] | None:
    """Build fail-closed current-tick signal context for payload logging only."""
    if not bool(traffic_lights_enabled):
        return None
    if red_route_points_ego is None or route_centerline_ego is None:
        return None
    red = np.asarray(red_route_points_ego, dtype=np.float64)
    if red.ndim != 2 or red.shape[0] < 1 or red.shape[1] < 2:
        return None
    progress = _route_progress_for_points(red[:, :2], route_centerline_ego)
    if progress is None:
        return None
    finite = np.isfinite(progress) & (progress >= -1e-6)
    if not np.any(finite):
        return None
    signal_s = float(np.min(np.maximum(progress[finite], 0.0)))
    return {
        "signal_s_m": signal_s,
        "current_phase": "red",
        "phase_remaining_s": None,
        "blocked_phases": ["red", "yellow"],
    }


def _shape_or_none(value: Any) -> list[int] | None:
    if value is None:
        return None
    return list(np.asarray(value).shape)


def _finite_nested(value: Any) -> bool:
    if value is None:
        return False
    array = np.asarray(value, dtype=np.float64)
    return bool(array.size > 0 and np.all(np.isfinite(array)))


def _wrap_angle(delta: np.ndarray) -> np.ndarray:
    return (np.asarray(delta, dtype=np.float64) + math.pi) % (2.0 * math.pi) - math.pi


def _candidate_headings(candidates: np.ndarray, horizon_steps: int) -> np.ndarray:
    trajectories = np.asarray(candidates, dtype=np.float64)
    horizon = min(max(int(horizon_steps), 2), int(trajectories.shape[1]))
    if trajectories.shape[2] >= 4:
        vectors = trajectories[:, :horizon, 2:4]
        norms = np.linalg.norm(vectors, axis=2)
        fallback = norms <= 1e-8
        headings = np.arctan2(vectors[:, :, 1], vectors[:, :, 0])
        if np.any(fallback):
            diffs = np.diff(trajectories[:, :horizon, :2], axis=1)
            diff_headings = np.arctan2(diffs[:, :, 1], diffs[:, :, 0])
            padded = np.concatenate([diff_headings[:, :1], diff_headings], axis=1)
            headings = np.where(fallback, padded, headings)
        return headings
    diffs = np.diff(trajectories[:, :horizon, :2], axis=1)
    headings = np.arctan2(diffs[:, :, 1], diffs[:, :, 0])
    return np.concatenate([headings[:, :1], headings], axis=1)


def _candidate_route_projection_details(
    candidates: np.ndarray,
    route_centerline: np.ndarray,
    horizon_steps: int,
) -> dict[str, Any]:
    centerline = np.asarray(route_centerline, dtype=np.float64)
    trajectories = np.asarray(candidates, dtype=np.float64)
    if trajectories.ndim != 3 or trajectories.shape[0] < 1 or trajectories.shape[2] < 2:
        raise ValueError("candidates must have shape [K,T,>=2].")
    horizon = min(max(int(horizon_steps), 2), int(trajectories.shape[1]))
    if centerline.ndim != 2 or centerline.shape[0] < 2 or centerline.shape[1] < 2:
        return {
            "candidate_route_segment_index": None,
            "candidate_route_projection_s_m": None,
            "candidate_route_lateral_error_m": None,
            "route_segment_count": 0,
        }

    starts_all = centerline[:-1, :2]
    ends_all = centerline[1:, :2]
    segments_all = ends_all - starts_all
    lengths_all = np.linalg.norm(segments_all, axis=1)
    valid = lengths_all > 1e-6
    if not np.any(valid):
        return {
            "candidate_route_segment_index": None,
            "candidate_route_projection_s_m": None,
            "candidate_route_lateral_error_m": None,
            "route_segment_count": 0,
        }
    valid_indices = np.flatnonzero(valid)
    starts = starts_all[valid]
    segments = segments_all[valid]
    lengths = lengths_all[valid]
    cumulative_all = np.concatenate([[0.0], np.cumsum(lengths_all)])
    cumulative_starts = cumulative_all[valid_indices]

    points = trajectories[:, :horizon, :2]
    flat = points.reshape(-1, 2)
    segment_indices = np.zeros(flat.shape[0], dtype=np.int32)
    projections_s = np.zeros(flat.shape[0], dtype=np.float64)
    lateral_errors = np.zeros(flat.shape[0], dtype=np.float64)
    for point_idx, point in enumerate(flat):
        rel = point.reshape(1, 2) - starts
        t = np.sum(rel * segments, axis=1) / np.maximum(lengths * lengths, 1e-12)
        t = np.clip(t, 0.0, 1.0)
        projected = starts + t.reshape(-1, 1) * segments
        distances = np.linalg.norm(projected - point.reshape(1, 2), axis=1)
        best = int(np.argmin(distances))
        segment = segments[best]
        point_rel = point - starts[best]
        cross = segment[0] * point_rel[1] - segment[1] * point_rel[0]
        segment_indices[point_idx] = int(valid_indices[best])
        projections_s[point_idx] = cumulative_starts[best] + t[best] * lengths[best]
        lateral_errors[point_idx] = cross / max(lengths[best], 1e-12)
    shape = points.shape[:2]
    return {
        "candidate_route_segment_index": segment_indices.reshape(shape),
        "candidate_route_projection_s_m": projections_s.reshape(shape),
        "candidate_route_lateral_error_m": lateral_errors.reshape(shape),
        "route_segment_count": int(centerline.shape[0] - 1),
    }


def _candidate_red_light_relation(
    candidates: np.ndarray,
    red_route_points: np.ndarray,
    horizon_steps: int,
) -> dict[str, Any]:
    red = np.asarray(red_route_points, dtype=np.float64)
    trajectories = np.asarray(candidates, dtype=np.float64)
    if trajectories.ndim != 3 or trajectories.shape[0] < 1 or trajectories.shape[2] < 2:
        raise ValueError("candidates must have shape [K,T,>=2].")
    horizon = min(max(int(horizon_steps), 2), int(trajectories.shape[1]))
    if red.ndim != 2 or red.shape[0] == 0 or red.shape[1] < 4:
        return {
            "candidate_red_stopline_distance_m": None,
            "candidate_red_heading_alignment": None,
            "red_route_point_count": 0,
        }
    red_xy = red[:, :2]
    red_dirs = red[:, 2:4]
    red_norms = np.linalg.norm(red_dirs, axis=1)
    valid = np.isfinite(red_norms) & (red_norms > 1e-8)
    if not np.any(valid):
        return {
            "candidate_red_stopline_distance_m": None,
            "candidate_red_heading_alignment": None,
            "red_route_point_count": int(red.shape[0]),
        }
    red_xy = red_xy[valid]
    red_dirs = red_dirs[valid] / red_norms[valid].reshape(-1, 1)
    points = trajectories[:, :horizon, :2]
    headings = _candidate_headings(trajectories, horizon)
    heading_vectors = np.stack((np.cos(headings), np.sin(headings)), axis=2)
    distances = np.zeros(points.shape[:2], dtype=np.float64)
    alignments = np.zeros(points.shape[:2], dtype=np.float64)
    for index in np.ndindex(points.shape[:2]):
        point = points[index]
        heading_vec = heading_vectors[index]
        deltas = red_xy - point.reshape(1, 2)
        ahead = np.sum(deltas * heading_vec.reshape(1, 2), axis=1) >= -1e-6
        candidate_red_xy = red_xy[ahead] if np.any(ahead) else red_xy
        candidate_dirs = red_dirs[ahead] if np.any(ahead) else red_dirs
        red_distances = np.linalg.norm(candidate_red_xy - point.reshape(1, 2), axis=1)
        best = int(np.argmin(red_distances))
        distances[index] = red_distances[best]
        alignments[index] = float(
            np.clip(np.dot(heading_vec, candidate_dirs[best]), -1.0, 1.0)
        )
    return {
        "candidate_red_stopline_distance_m": distances,
        "candidate_red_heading_alignment": alignments,
        "red_route_point_count": int(red.shape[0]),
    }


def _red_route_vector_logging_payload(
    *,
    candidates: np.ndarray,
    red_route_points: np.ndarray,
    traffic_light_steps: int,
    latency_ms: float = 0.0,
) -> dict[str, Any]:
    trajectories = np.asarray(candidates, dtype=np.float64)
    if trajectories.ndim != 3 or trajectories.shape[0] < 1 or trajectories.shape[2] < 2:
        raise ValueError("candidates must have shape [K,T,>=2].")
    horizon = min(max(int(traffic_light_steps), 2), int(trajectories.shape[1]))
    points = trajectories[:, :horizon, :2]
    headings = _candidate_headings(trajectories, horizon)
    heading_vectors = np.stack((np.cos(headings), np.sin(headings)), axis=2)
    red = np.asarray(red_route_points, dtype=np.float64)
    red_points = (
        np.asarray(red[:, :4], dtype=np.float64)
        if red.ndim == 2 and red.shape[0] > 0 and red.shape[1] >= 4
        else np.zeros((0, 4), dtype=np.float64)
    )
    selected_indices = np.full(points.shape[:2], -1, dtype=np.int32)
    vectors_to_selected = np.zeros((*points.shape[:2], 2), dtype=np.float64)
    current_alignment = np.zeros(points.shape[:2], dtype=np.float64)
    reverse_alignment = np.zeros(points.shape[:2], dtype=np.float64)
    valid_red_count = 0

    if red_points.shape[0] > 0:
        red_xy = red_points[:, :2]
        red_dirs = red_points[:, 2:4]
        red_norms = np.linalg.norm(red_dirs, axis=1)
        valid = np.isfinite(red_norms) & (red_norms > 1e-8)
        valid_red_count = int(np.count_nonzero(valid))
        if valid_red_count > 0:
            valid_indices = np.nonzero(valid)[0]
            valid_xy = red_xy[valid]
            valid_dirs = red_dirs[valid] / red_norms[valid].reshape(-1, 1)
            for index in np.ndindex(points.shape[:2]):
                point = points[index]
                heading_vec = heading_vectors[index]
                deltas = valid_xy - point.reshape(1, 2)
                ahead = np.sum(deltas * heading_vec.reshape(1, 2), axis=1) >= -1e-6
                candidate_xy = valid_xy[ahead] if np.any(ahead) else valid_xy
                candidate_dirs = valid_dirs[ahead] if np.any(ahead) else valid_dirs
                candidate_indices = valid_indices[ahead] if np.any(ahead) else valid_indices
                distances = np.linalg.norm(candidate_xy - point.reshape(1, 2), axis=1)
                best = int(np.argmin(distances))
                selected_indices[index] = int(candidate_indices[best])
                vectors_to_selected[index] = candidate_xy[best] - point
                current = float(
                    np.clip(np.dot(heading_vec, candidate_dirs[best]), -1.0, 1.0)
                )
                current_alignment[index] = current
                reverse_alignment[index] = -current

    payload = {
        "schema_version": RED_ROUTE_VECTOR_LOGGING_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "definition": (
            "current-tick red route point vectors and candidate heading vectors "
            "computed from fixed DP candidates before closed-loop outcome labels"
        ),
        "candidate_count": int(trajectories.shape[0]),
        "horizons": {"traffic_light_steps": horizon},
        "red_route_point_count": int(red_points.shape[0]),
        "valid_red_route_point_count": valid_red_count,
        "field_shapes": {},
        "finite_checks": {},
        "latency_ms": {"latency_ms_red_route_vector_logging": float(latency_ms)},
        "red_route_points_ego_xy_dir": red_points.tolist(),
        "candidate_red_selected_route_point_index": selected_indices.tolist(),
        "candidate_red_heading_vector_xy": heading_vectors.tolist(),
        "candidate_red_vector_to_selected_point_xy": vectors_to_selected.tolist(),
        "candidate_red_alignment_recomputed_current": current_alignment.tolist(),
        "candidate_red_alignment_recomputed_reverse": reverse_alignment.tolist(),
    }
    for field in RED_ROUTE_VECTOR_FIELDS:
        payload["field_shapes"][field] = (
            list(red_points.shape)
            if field == "red_route_points_ego_xy_dir"
            else _shape_or_none(payload[field])
        )
    payload["finite_checks"] = {
        "red_route_points_ego_xy_dir": bool(np.all(np.isfinite(red_points))),
        "candidate_red_selected_route_point_index": bool(
            selected_indices.shape == points.shape[:2]
            and np.all(selected_indices >= -1)
        ),
        "candidate_red_heading_vector_xy": _finite_nested(heading_vectors),
        "candidate_red_vector_to_selected_point_xy": _finite_nested(
            vectors_to_selected
        ),
        "candidate_red_alignment_recomputed_current": _finite_nested(
            current_alignment
        ),
        "candidate_red_alignment_recomputed_reverse": _finite_nested(
            reverse_alignment
        ),
    }
    return payload


def _candidate_route_heading_change(
    candidates: np.ndarray,
    horizon_steps: int,
) -> np.ndarray:
    headings = _candidate_headings(candidates, horizon_steps)
    return _wrap_angle(np.diff(headings, axis=1))


def _route_curvature_context_abs(
    route_centerline: np.ndarray,
    horizon_steps: int,
) -> np.ndarray | None:
    centerline = np.asarray(route_centerline, dtype=np.float64)
    horizon = max(int(horizon_steps), 2)
    if centerline.ndim != 2 or centerline.shape[0] < 2 or centerline.shape[1] < 2:
        return None
    points = centerline[: min(horizon, centerline.shape[0]), :2]
    segments = np.diff(points, axis=0)
    valid = np.linalg.norm(segments, axis=1) > 1e-6
    if not np.any(valid):
        return None
    headings = np.arctan2(segments[valid, 1], segments[valid, 0])
    if headings.size < 2:
        return np.zeros(0, dtype=np.float64)
    return np.abs(_wrap_angle(np.diff(headings)))


def _observable_state_logging_payload(
    *,
    candidates: np.ndarray,
    route_centerline_ego: np.ndarray,
    red_route_points: np.ndarray,
    candidate_obstacle_clearance: dict[str, Any] | None,
    support_steps: int,
    traffic_light_steps: int,
    turn_steps: int,
    neighbor_clearance_latency_ms: float = 0.0,
) -> dict[str, Any]:
    trajectories = np.asarray(candidates, dtype=np.float64)
    if trajectories.ndim != 3 or trajectories.shape[0] < 1 or trajectories.shape[1] < 2:
        raise ValueError("candidates must have shape [K,T,>=2].")
    route_start = time.perf_counter()
    route = _candidate_route_projection_details(
        trajectories,
        route_centerline_ego,
        support_steps,
    )
    route_done = time.perf_counter()
    traffic = _candidate_red_light_relation(
        trajectories,
        red_route_points,
        traffic_light_steps,
    )
    traffic_done = time.perf_counter()
    heading_change = _candidate_route_heading_change(trajectories, turn_steps)
    route_curvature = _route_curvature_context_abs(route_centerline_ego, turn_steps)
    turn_done = time.perf_counter()
    clearance = candidate_obstacle_clearance or {}
    min_clearance = clearance.get("min_obstacle_clearance_lower_bound_m")
    obstacle_slots = clearance.get("obstacle_slots")
    candidate_count = int(trajectories.shape[0])
    finite_checks = {
        "candidate_route_segment_index": (
            route["candidate_route_segment_index"] is not None
            and np.asarray(route["candidate_route_segment_index"]).shape[0] == candidate_count
        ),
        "candidate_route_projection_s_m": _finite_nested(
            route["candidate_route_projection_s_m"]
        ),
        "candidate_route_lateral_error_m": _finite_nested(
            route["candidate_route_lateral_error_m"]
        ),
        "candidate_red_stopline_distance_m": (
            traffic["candidate_red_stopline_distance_m"] is None
            if int(traffic["red_route_point_count"]) == 0
            else _finite_nested(traffic["candidate_red_stopline_distance_m"])
        ),
        "candidate_red_heading_alignment": (
            traffic["candidate_red_heading_alignment"] is None
            if int(traffic["red_route_point_count"]) == 0
            else _finite_nested(traffic["candidate_red_heading_alignment"])
        ),
        "candidate_route_heading_change_rad": _finite_nested(heading_change),
        "route_curvature_context_abs": (
            route_curvature is not None
            and bool(np.all(np.isfinite(route_curvature)))
        ),
        "candidate_min_obstacle_clearance_lower_bound_m": (
            isinstance(min_clearance, list)
            and len(min_clearance) == candidate_count
            and all(value is None or np.isfinite(float(value)) for value in min_clearance)
        ),
        "candidate_obstacle_slot_count": (
            isinstance(obstacle_slots, list)
            and len(obstacle_slots) == candidate_count
            and all(int(value) >= 0 for value in obstacle_slots)
        ),
    }
    payload = {
        "schema_version": OBSERVABLE_STATE_LOGGING_SCHEMA_VERSION,
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "future_outcome_leakage": False,
        "definition": (
            "current-tick route, traffic-light, turn-context, and neighbor "
            "descriptors computed from fixed DP candidates before closed-loop "
            "outcome labels"
        ),
        "candidate_count": candidate_count,
        "horizons": {
            "support_steps": min(max(int(support_steps), 2), int(trajectories.shape[1])),
            "traffic_light_steps": min(
                max(int(traffic_light_steps), 2),
                int(trajectories.shape[1]),
            ),
            "turn_steps": min(max(int(turn_steps), 2), int(trajectories.shape[1])),
        },
        "route_segment_count": int(route["route_segment_count"]),
        "red_route_point_count": int(traffic["red_route_point_count"]),
        "field_shapes": {},
        "finite_checks": finite_checks,
        "latency_ms": {
            "latency_ms_observable_state_route_topology": (
                route_done - route_start
            )
            * 1000.0,
            "latency_ms_observable_state_traffic_light_relation": (
                traffic_done - route_done
            )
            * 1000.0,
            "latency_ms_observable_state_route_turn": (
                turn_done - traffic_done
            )
            * 1000.0,
            "latency_ms_observable_state_neighbor_clearance": float(
                neighbor_clearance_latency_ms
            ),
        },
        "candidate_route_segment_index": (
            None
            if route["candidate_route_segment_index"] is None
            else route["candidate_route_segment_index"].tolist()
        ),
        "candidate_route_projection_s_m": (
            None
            if route["candidate_route_projection_s_m"] is None
            else route["candidate_route_projection_s_m"].tolist()
        ),
        "candidate_route_lateral_error_m": (
            None
            if route["candidate_route_lateral_error_m"] is None
            else route["candidate_route_lateral_error_m"].tolist()
        ),
        "candidate_red_stopline_distance_m": (
            None
            if traffic["candidate_red_stopline_distance_m"] is None
            else traffic["candidate_red_stopline_distance_m"].tolist()
        ),
        "candidate_red_heading_alignment": (
            None
            if traffic["candidate_red_heading_alignment"] is None
            else traffic["candidate_red_heading_alignment"].tolist()
        ),
        "candidate_route_heading_change_rad": heading_change.tolist(),
        "route_curvature_context_abs": (
            None if route_curvature is None else route_curvature.tolist()
        ),
        "candidate_min_obstacle_clearance_lower_bound_m": min_clearance,
        "candidate_obstacle_slot_count": obstacle_slots,
    }
    for field in (
        "candidate_route_segment_index",
        "candidate_route_projection_s_m",
        "candidate_route_lateral_error_m",
        "candidate_red_stopline_distance_m",
        "candidate_red_heading_alignment",
        "candidate_route_heading_change_rad",
        "route_curvature_context_abs",
        "candidate_min_obstacle_clearance_lower_bound_m",
        "candidate_obstacle_slot_count",
    ):
        payload["field_shapes"][field] = _shape_or_none(payload[field])
    return payload


def _apply_candidate0_route_progress_guard(
    feasible: np.ndarray | None,
    reasons: tuple[tuple[str, ...], ...] | None,
    candidate_route_progress: np.ndarray | None,
    min_candidate0_route_progress_ratio: float | None,
) -> tuple[np.ndarray | None, tuple[tuple[str, ...], ...] | None]:
    if (
        min_candidate0_route_progress_ratio is None
        or candidate_route_progress is None
    ):
        return feasible, reasons
    progress = np.asarray(candidate_route_progress, dtype=np.float64).reshape(-1)
    if progress.size == 0:
        return feasible, reasons
    if feasible is None:
        feasible_arr = np.ones(progress.shape[0], dtype=bool)
    else:
        feasible_arr = np.asarray(feasible, dtype=bool).reshape(-1).copy()
    if feasible_arr.shape != progress.shape:
        raise ValueError(
            "candidate_route_progress must match feasible candidate count."
        )
    reason_rows = (
        [[] for _ in range(progress.shape[0])]
        if reasons is None
        else [list(row) for row in reasons]
    )
    candidate0_progress = float(progress[0])
    if candidate0_progress <= 0.0 or not np.isfinite(candidate0_progress):
        return feasible_arr, tuple(tuple(row) for row in reason_rows)
    threshold = candidate0_progress * float(min_candidate0_route_progress_ratio)
    for idx, value in enumerate(progress):
        if idx == 0 or not feasible_arr[idx]:
            continue
        if not np.isfinite(value) or float(value) < threshold:
            feasible_arr[idx] = False
            reason_rows[idx].append("route_candidate0_underprogress")
    return feasible_arr, tuple(tuple(row) for row in reason_rows)


def _candidate_step_reach(candidates: np.ndarray) -> np.ndarray:
    candidate_xy = np.asarray(candidates, dtype=np.float64)[..., :2]
    if candidate_xy.ndim != 3 or candidate_xy.shape[1] < 1:
        raise ValueError("candidates must have shape [K, T, >=2].")
    reach = np.linalg.norm(candidate_xy[:, 0, :], axis=1)
    return np.nan_to_num(reach, nan=0.0, posinf=0.0, neginf=0.0)


def _current_perfect_tracker_state(agent: Any) -> tuple[float, float]:
    heading = float(agent.current_heading)
    forward = np.array([math.cos(heading), math.sin(heading)], dtype=np.float64)
    velocity = np.asarray(agent.current_velocity, dtype=np.float64).reshape(-1)
    acceleration = np.asarray(agent.acceleration, dtype=np.float64).reshape(-1)
    if velocity.size < 2 or acceleration.size < 2:
        raise ValueError("Agent velocity and acceleration must contain xy values.")
    speed = max(float(np.dot(velocity[:2], forward)), 0.0)
    longitudinal_acceleration = float(np.dot(acceleration[:2], forward))
    if not np.isfinite(speed) or not np.isfinite(longitudinal_acceleration):
        raise ValueError("Perfect-tracker state must be finite.")
    return speed, longitudinal_acceleration


def _current_acceleration_ego_xy(agent: Any, dt: float) -> np.ndarray:
    if not np.isfinite(dt) or dt <= 0.0:
        raise ValueError("PerfectTracker dt must be finite and positive.")
    heading = float(agent.current_heading)
    acceleration = None
    velocities = np.asarray(
        getattr(agent, "past_velocities", []),
        dtype=np.float64,
    )
    if (
        velocities.ndim == 2
        and velocities.shape[0] >= 2
        and velocities.shape[1] >= 2
        and np.all(np.isfinite(velocities[-2:, :2]))
    ):
        acceleration = (velocities[-1, :2] - velocities[-2, :2]) / float(dt)
    if acceleration is None:
        acceleration = np.asarray(
            agent.acceleration,
            dtype=np.float64,
        ).reshape(-1)
    if acceleration.size < 2 or not np.all(np.isfinite(acceleration[:2])):
        raise ValueError("Agent acceleration must contain finite xy values.")
    forward = np.array([math.cos(heading), math.sin(heading)], dtype=np.float64)
    lateral = np.array([-math.sin(heading), math.cos(heading)], dtype=np.float64)
    return np.array(
        [
            float(np.dot(acceleration[:2], forward)),
            float(np.dot(acceleration[:2], lateral)),
        ],
        dtype=np.float64,
    )


def _apply_candidate0_step_reach_guard(
    feasible: np.ndarray | None,
    reasons: tuple[tuple[str, ...], ...] | None,
    candidate_step_reach: np.ndarray,
    min_candidate0_step_reach_ratio: float | None,
    preserve_any_feasible: bool = False,
) -> tuple[np.ndarray | None, tuple[tuple[str, ...], ...] | None, bool]:
    if min_candidate0_step_reach_ratio is None:
        return feasible, reasons, False
    reach = np.asarray(candidate_step_reach, dtype=np.float64).reshape(-1)
    if reach.size == 0:
        return feasible, reasons, False
    if feasible is None:
        feasible_arr = np.ones(reach.shape[0], dtype=bool)
    else:
        feasible_arr = np.asarray(feasible, dtype=bool).reshape(-1).copy()
    if feasible_arr.shape != reach.shape:
        raise ValueError("candidate_step_reach must match feasible candidate count.")
    original_feasible_arr = feasible_arr.copy()
    reason_rows = (
        [[] for _ in range(reach.shape[0])]
        if reasons is None
        else [list(row) for row in reasons]
    )
    original_reason_rows = [list(row) for row in reason_rows]
    candidate0_reach = float(reach[0])
    if candidate0_reach <= 0.0 or not np.isfinite(candidate0_reach):
        return feasible_arr, tuple(tuple(row) for row in reason_rows), False
    threshold = candidate0_reach * float(min_candidate0_step_reach_ratio)
    for idx, value in enumerate(reach):
        if idx == 0 or not feasible_arr[idx]:
            continue
        if not np.isfinite(value) or float(value) < threshold:
            feasible_arr[idx] = False
            reason_rows[idx].append("candidate0_step_reach_underprogress")
    relaxed = bool(
        preserve_any_feasible and original_feasible_arr.any() and not feasible_arr.any()
    )
    if relaxed:
        return (
            original_feasible_arr,
            tuple(tuple(row) for row in original_reason_rows),
            True,
        )
    return feasible_arr, tuple(tuple(row) for row in reason_rows), False


def _apply_lexicographic_admissible_filter(
    feasible: np.ndarray | None,
    reasons: tuple[tuple[str, ...], ...] | None,
    *,
    candidate_progress: np.ndarray,
    candidate_planned_red_light_cost: np.ndarray,
    candidate_dp_prior_jerk_excess_cost: np.ndarray,
    candidate_horizon_lateral_acceleration_cost: np.ndarray,
    progress_epsilon_m: float | None,
    red_epsilon: float,
    jerk_epsilon: float,
    lateral_epsilon: float,
) -> tuple[
    np.ndarray | None,
    tuple[tuple[str, ...], ...] | None,
    dict[str, int] | None,
]:
    if progress_epsilon_m is None:
        return feasible, reasons, None
    epsilons = (
        progress_epsilon_m,
        red_epsilon,
        jerk_epsilon,
        lateral_epsilon,
    )
    if any(not np.isfinite(value) or value < 0.0 for value in epsilons):
        raise ValueError(
            "Lexicographic epsilons must be finite and nonnegative."
        )
    arrays = {
        "progress": np.asarray(candidate_progress, dtype=np.float64).reshape(-1),
        "planned_red": np.asarray(
            candidate_planned_red_light_cost, dtype=np.float64
        ).reshape(-1),
        "jerk": np.asarray(
            candidate_dp_prior_jerk_excess_cost, dtype=np.float64
        ).reshape(-1),
        "lateral": np.asarray(
            candidate_horizon_lateral_acceleration_cost, dtype=np.float64
        ).reshape(-1),
    }
    candidate_count = arrays["progress"].size
    if candidate_count == 0:
        raise ValueError("Lexicographic preselection requires candidates.")
    if any(values.shape != (candidate_count,) for values in arrays.values()):
        raise ValueError(
            "Lexicographic preselection fields must have equal candidate count."
        )
    if any(not np.all(np.isfinite(values)) for values in arrays.values()):
        raise ValueError("Lexicographic preselection fields must be finite.")
    if np.any(arrays["planned_red"] < 0.0):
        raise ValueError("Lexicographic planned-red costs must be nonnegative.")
    if np.any(arrays["jerk"] < 0.0):
        raise ValueError("Lexicographic jerk costs must be nonnegative.")
    if np.any(arrays["lateral"] < 0.0):
        raise ValueError("Lexicographic lateral costs must be nonnegative.")
    if feasible is None:
        feasible_arr = np.ones(candidate_count, dtype=bool)
    else:
        feasible_arr = np.asarray(feasible, dtype=bool).reshape(-1).copy()
    if feasible_arr.shape != (candidate_count,):
        raise ValueError(
            "Lexicographic fields must match feasible candidate count."
        )
    reason_rows = (
        [[] for _ in range(candidate_count)]
        if reasons is None
        else [list(row) for row in reasons]
    )
    if len(reason_rows) != candidate_count:
        raise ValueError(
            "Lexicographic reasons must match feasible candidate count."
        )
    stage_counts = {"base": int(feasible_arr.sum())}
    if not feasible_arr.any():
        stage_counts.update({"progress": 0, "planned_red": 0, "jerk": 0, "lateral": 0})
        return feasible_arr, tuple(tuple(row) for row in reason_rows), stage_counts

    stages = (
        (
            "progress",
            arrays["progress"],
            float(np.max(arrays["progress"][feasible_arr]))
            - float(progress_epsilon_m),
            "min",
            "lexicographic_progress",
        ),
        (
            "planned_red",
            arrays["planned_red"],
            None,
            "max",
            "lexicographic_planned_red",
        ),
        (
            "jerk",
            arrays["jerk"],
            None,
            "max",
            "lexicographic_jerk",
        ),
        (
            "lateral",
            arrays["lateral"],
            None,
            "max",
            "lexicographic_lateral",
        ),
    )
    tolerances = {
        "planned_red": float(red_epsilon),
        "jerk": float(jerk_epsilon),
        "lateral": float(lateral_epsilon),
    }
    for stage_name, values, threshold, comparison, reason in stages:
        active = feasible_arr.copy()
        if threshold is None:
            threshold = float(np.min(values[active])) + tolerances[stage_name]
        if comparison == "min":
            keep = values >= threshold - 1e-12
        else:
            keep = values <= threshold + 1e-12
        removed = active & ~keep
        feasible_arr[removed] = False
        for idx in np.flatnonzero(removed):
            reason_rows[int(idx)].append(reason)
        if not feasible_arr.any():
            raise RuntimeError(
                f"Lexicographic stage {stage_name} unexpectedly removed all candidates."
            )
        stage_counts[stage_name] = int(feasible_arr.sum())
    return feasible_arr, tuple(tuple(row) for row in reason_rows), stage_counts


def _apply_underprogress_relaxation_override(
    selection: CAMPSelectionResult,
    candidates: np.ndarray,
    *,
    candidate_progress: np.ndarray,
    candidate_union_red_cost: np.ndarray,
    candidate_red_stopping_margin_cost: np.ndarray,
    perfect_tracker_open_loop: dict[Any, Any],
    progress_loss_budget_m: float,
    h3_distance_loss_budget_m: float,
    lateral_limit_mps2: float,
) -> tuple[CAMPSelectionResult, dict[str, Any]]:
    selected = int(selection.selected_index)
    feasible = np.asarray(selection.feasible_mask, dtype=bool).reshape(-1)
    candidate_count = feasible.size
    reasons = [tuple(row) for row in selection.infeasibility_reasons]
    if len(reasons) != candidate_count:
        raise ValueError("Underprogress relaxation reasons must match candidates.")
    progress = np.asarray(candidate_progress, dtype=np.float64).reshape(-1)
    union_red = np.asarray(candidate_union_red_cost, dtype=np.float64).reshape(-1)
    stopping_margin = np.asarray(
        candidate_red_stopping_margin_cost,
        dtype=np.float64,
    ).reshape(-1)
    horizons = perfect_tracker_open_loop.get("horizons")
    h3 = None
    if isinstance(horizons, dict):
        h3 = horizons.get("3")
        if h3 is None:
            h3 = horizons.get(3)
    if h3 is None:
        h3 = perfect_tracker_open_loop.get("3")
    if h3 is None:
        h3 = perfect_tracker_open_loop.get(3)
    if not isinstance(h3, dict):
        raise ValueError("Underprogress relaxation requires H3 rollout metrics.")
    distance = np.asarray(h3["distance_m"], dtype=np.float64).reshape(-1)
    h3_lateral = np.asarray(
        h3["max_lateral_acceleration_mps2"],
        dtype=np.float64,
    ).reshape(-1)
    arrays = (progress, union_red, stopping_margin, distance, h3_lateral)
    if any(array.shape != (candidate_count,) for array in arrays):
        raise ValueError("Underprogress relaxation fields must match candidates.")
    if any(not np.all(np.isfinite(array)) for array in arrays):
        raise ValueError("Underprogress relaxation fields must be finite.")
    if np.any(union_red < 0.0) or np.any(stopping_margin < 0.0):
        raise ValueError("Underprogress relaxation costs must be nonnegative.")

    stats: dict[str, Any] = {
        "enabled": True,
        "changed": False,
        "baseline_selected_index": selected,
        "selected_index": selected,
        "candidate_count": candidate_count,
        "budget": {
            "progress_loss_m": float(progress_loss_budget_m),
            "h3_distance_loss_m": float(h3_distance_loss_budget_m),
            "h3_max_lateral_limit_mps2": float(lateral_limit_mps2),
            "requires_stopping_margin_nonworse": True,
            "ignored_reason": "dp_underprogress",
        },
        "reason": "not_evaluated",
    }
    if selection.used_fallback or not feasible.any():
        stats["reason"] = "fallback_or_no_base_feasible_candidate"
        return selection, stats
    if union_red[selected] <= 0.0:
        stats["reason"] = "baseline_union_red_zero"
        return selection, stats

    lower_base_feasible = feasible & (union_red < union_red[selected])
    lower_base_feasible[selected] = False
    if lower_base_feasible.any():
        stats["reason"] = "lower_red_base_feasible_candidate_exists"
        stats["lower_red_base_feasible_candidates"] = int(
            lower_base_feasible.sum()
        )
        return selection, stats

    only_underprogress = np.asarray(
        [row == ("dp_underprogress",) for row in reasons],
        dtype=bool,
    )
    admissible = (
        only_underprogress
        & (union_red < union_red[selected])
        & (progress >= progress[selected] - float(progress_loss_budget_m))
        & (distance >= distance[selected] - float(h3_distance_loss_budget_m))
        & (stopping_margin <= stopping_margin[selected] + 1e-12)
        & (h3_lateral <= float(lateral_limit_mps2))
    )
    admissible[selected] = False
    indices = np.flatnonzero(admissible)
    stats["admissible_candidates"] = int(indices.size)
    if not indices.size:
        stats["reason"] = "no_underprogress_relaxed_candidate"
        return selection, stats

    chosen = min(
        indices.tolist(),
        key=lambda idx: (
            float(union_red[idx]),
            float(stopping_margin[idx]),
            float(selection.scores[idx]),
            int(idx),
        ),
    )
    effective_feasible = feasible.copy()
    effective_feasible[indices] = True
    effective_reasons = [list(row) for row in reasons]
    for idx in indices.tolist():
        effective_reasons[idx] = []
    effective_selection_scores = np.asarray(
        selection.selection_scores,
        dtype=np.float64,
    ).copy()
    effective_selection_scores[indices] = selection.scores[indices]
    stats.update(
        {
            "changed": True,
            "reason": "underprogress_relaxed_lower_red_candidate",
            "selected_index": int(chosen),
            "admissible_indices": [int(idx) for idx in indices.tolist()],
            "delta": {
                "union_red": float(union_red[chosen] - union_red[selected]),
                "progress_m": float(progress[chosen] - progress[selected]),
                "h3_distance_m": float(distance[chosen] - distance[selected]),
                "red_stopping_margin": float(
                    stopping_margin[chosen] - stopping_margin[selected]
                ),
                "h3_max_lateral_mps2": float(
                    h3_lateral[chosen] - h3_lateral[selected]
                ),
            },
        }
    )
    return (
        replace(
            selection,
            selected_index=int(chosen),
            selected_trajectory=candidates[chosen].copy(),
            feasible_mask=effective_feasible,
            infeasibility_reasons=tuple(
                tuple(row) for row in effective_reasons
            ),
            selection_scores=effective_selection_scores,
            used_fallback=False,
        ),
        stats,
    )


def _candidate_vector(
    values: Any,
    *,
    candidate_count: int,
    field_name: str,
) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64).reshape(-1)
    if array.shape != (candidate_count,):
        raise ValueError(f"{field_name} must match candidate count.")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{field_name} must be finite.")
    return array


def _perfect_tracker_horizon_distance(
    perfect_tracker_open_loop: dict[Any, Any],
    horizon: int,
) -> np.ndarray:
    horizons = perfect_tracker_open_loop.get("horizons")
    metrics = None
    if isinstance(horizons, dict):
        metrics = horizons.get(str(horizon))
        if metrics is None:
            metrics = horizons.get(int(horizon))
    if metrics is None:
        metrics = perfect_tracker_open_loop.get(str(horizon))
    if metrics is None:
        metrics = perfect_tracker_open_loop.get(int(horizon))
    if not isinstance(metrics, dict) or "distance_m" not in metrics:
        raise ValueError(
            f"Traffic-light hybrid postselection requires H{horizon} distance."
        )
    return np.asarray(metrics["distance_m"], dtype=np.float64).reshape(-1)


def _loss(values: np.ndarray, selected: int) -> np.ndarray:
    return np.maximum(values[int(selected)] - values, 0.0)


def _traffic_light_hybrid_budget(mode: str) -> dict[str, float]:
    try:
        return dict(TRAFFIC_LIGHT_HYBRID_POSTSELECTION_BUDGETS[mode])
    except KeyError as exc:
        raise ValueError(f"Unknown traffic-light hybrid mode: {mode}") from exc


def _is_state_redroute_top1_floor_mode(mode: str) -> bool:
    return mode in STATE_REDROUTE_TOP1_FLOOR_MODES


def _apply_state_redroute_top1_floor(
    selection: CAMPSelectionResult,
    *,
    mode: str,
    selected: int,
    candidate_count: int,
    red_route_point_count: int,
    candidate_union_red_cost: np.ndarray,
    candidate_red_stopping_margin_cost: np.ndarray,
    candidate_dp_prior_jerk_excess_cost: np.ndarray,
    candidate_horizon_lateral_acceleration_cost: np.ndarray,
) -> tuple[int, dict[str, Any]]:
    if mode not in STATE_REDROUTE_TOP1_FLOOR_MODES:
        raise ValueError(f"Unknown state red-route Top-1 floor mode: {mode}")
    feasible = np.asarray(selection.feasible_mask, dtype=bool).reshape(-1)
    if feasible.shape != (candidate_count,):
        raise ValueError("State red-route Top-1 floor feasible mask shape mismatch.")
    require_lateral_nonworse = (
        mode == STATE_REDROUTE_TOP1_FLOOR_LATERAL_NONWORSE_MODE
    )
    union_red = _candidate_vector(
        candidate_union_red_cost,
        candidate_count=candidate_count,
        field_name="candidate_union_red_cost",
    )
    red_stopping = _candidate_vector(
        candidate_red_stopping_margin_cost,
        candidate_count=candidate_count,
        field_name="candidate_red_stopping_margin_cost",
    )
    raw_jerk = _candidate_vector(
        candidate_dp_prior_jerk_excess_cost,
        candidate_count=candidate_count,
        field_name="candidate_dp_prior_jerk_excess_cost",
    )
    raw_lateral = _candidate_vector(
        candidate_horizon_lateral_acceleration_cost,
        candidate_count=candidate_count,
        field_name="candidate_horizon_lateral_acceleration_cost",
    )
    for field_name, values in (
        ("candidate_union_red_cost", union_red),
        ("candidate_red_stopping_margin_cost", red_stopping),
        ("candidate_dp_prior_jerk_excess_cost", raw_jerk),
        ("candidate_horizon_lateral_acceleration_cost", raw_lateral),
    ):
        if np.any(values < 0.0):
            raise ValueError(f"{field_name} must be nonnegative.")

    budgets = _traffic_light_hybrid_budget(mode)
    stats: dict[str, Any] = {
        "schema_version": "traffic_light_hybrid_postselection_v1",
        "enabled": True,
        "default_off": True,
        "selection_effect": True,
        "online_selector_change": True,
        "future_outcome_leakage": False,
        "classical_benders_claim": False,
        "mode": str(mode),
        "screen_name": f"traffic_light_hybrid_{mode}",
        "state_gate": "red_route_point_count_positive",
        "red_route_point_count": int(red_route_point_count),
        "candidate0_feasible": bool(feasible[0]),
        "candidate0_feasible_required": False,
        "floor_candidate_index": 0,
        "checks": ["union_red", "red_stopping", "proxy_jerk"],
        "baseline_selected_index": int(selected),
        "selected_index": int(selected),
        "changed": False,
        "opportunity": False,
        "candidate_count": int(candidate_count),
        "admissible_candidates": 0,
        "budgets": budgets,
        "requires": {
            "red_route_point_count_positive": True,
            "candidate0_feasible": False,
            "selected_worse_than_top1_on_any_check": True,
            "candidate0_horizon_lateral_nonworse": require_lateral_nonworse,
        },
        "trigger_reasons": [],
        "reason": "not_evaluated",
    }
    if int(red_route_point_count) <= 0:
        stats["reason"] = "red_route_point_count_not_positive"
        return int(selected), stats
    if int(selected) == 0:
        stats["reason"] = "baseline_is_top1"
        return int(selected), stats

    trigger_reasons: list[str] = []
    if union_red[selected] - union_red[0] > TRAFFIC_LIGHT_HYBRID_TOL:
        trigger_reasons.append("union_red")
    if red_stopping[selected] - red_stopping[0] > TRAFFIC_LIGHT_HYBRID_TOL:
        trigger_reasons.append("red_stopping")
    if raw_jerk[selected] - raw_jerk[0] > TRAFFIC_LIGHT_HYBRID_TOL:
        trigger_reasons.append("proxy_jerk")
    if not trigger_reasons:
        stats["reason"] = "top1_not_better_on_red_or_proxy_jerk"
        return int(selected), stats

    lateral_delta = float(raw_lateral[0] - raw_lateral[selected])
    if require_lateral_nonworse and lateral_delta > TRAFFIC_LIGHT_HYBRID_TOL:
        stats.update(
            {
                "opportunity": True,
                "reason": "top1_horizon_lateral_worse",
                "trigger_reasons": trigger_reasons,
                "losses": {
                    "candidate0_horizon_lateral_cost_delta": lateral_delta,
                },
                "delta": {
                    "union_red": float(union_red[0] - union_red[selected]),
                    "red_stopping": float(red_stopping[0] - red_stopping[selected]),
                    "raw_jerk": float(raw_jerk[0] - raw_jerk[selected]),
                    "horizon_lateral": lateral_delta,
                },
            }
        )
        return int(selected), stats

    stats.update(
        {
            "changed": True,
            "opportunity": True,
            "reason": "selected_state_redroute_top1_floor_candidate",
            "selected_index": 0,
            "admissible_candidates": 1,
            "admissible_indices": [0],
            "trigger_reasons": trigger_reasons,
            "losses": {},
            "delta": {
                "union_red": float(union_red[0] - union_red[selected]),
                "red_stopping": float(red_stopping[0] - red_stopping[selected]),
                "raw_jerk": float(raw_jerk[0] - raw_jerk[selected]),
                "horizon_lateral": lateral_delta,
            },
        }
    )
    return 0, stats


def _apply_traffic_light_hybrid_postselection(
    selection: CAMPSelectionResult,
    *,
    traffic_lights_enabled: bool,
    mode: str,
    candidate_step_reach: np.ndarray,
    candidate_progress: np.ndarray,
    candidate_union_red_cost: np.ndarray,
    candidate_red_stopping_margin_cost: np.ndarray,
    candidate_dp_prior_jerk_excess_cost: np.ndarray,
    candidate_horizon_lateral_acceleration_cost: np.ndarray,
    candidate_target_speed_mps: np.ndarray,
    perfect_tracker_open_loop: dict[Any, Any],
    red_route_point_count: int | None = None,
) -> tuple[int, dict[str, Any]]:
    selected = int(selection.selected_index)
    feasible = np.asarray(selection.feasible_mask, dtype=bool).reshape(-1)
    candidate_count = feasible.size
    if selected < 0 or selected >= candidate_count:
        raise ValueError("Traffic-light hybrid selected_index is out of range.")
    if _is_state_redroute_top1_floor_mode(mode):
        return _apply_state_redroute_top1_floor(
            selection,
            mode=mode,
            selected=selected,
            candidate_count=candidate_count,
            red_route_point_count=(
                0 if red_route_point_count is None else int(red_route_point_count)
            ),
            candidate_union_red_cost=candidate_union_red_cost,
            candidate_red_stopping_margin_cost=(
                candidate_red_stopping_margin_cost
            ),
            candidate_dp_prior_jerk_excess_cost=(
                candidate_dp_prior_jerk_excess_cost
            ),
            candidate_horizon_lateral_acceleration_cost=(
                candidate_horizon_lateral_acceleration_cost
            ),
        )
    scores = np.asarray(selection.selection_scores, dtype=np.float64).reshape(-1)
    if scores.shape != (candidate_count,):
        raise ValueError("selection_scores must match candidate count.")
    if not np.all(np.isfinite(scores[feasible])):
        raise ValueError("selection_scores must be finite for feasible candidates.")
    progress = _candidate_vector(
        candidate_progress,
        candidate_count=candidate_count,
        field_name="candidate_progress",
    )
    union_red = _candidate_vector(
        candidate_union_red_cost,
        candidate_count=candidate_count,
        field_name="candidate_union_red_cost",
    )
    red_stopping = _candidate_vector(
        candidate_red_stopping_margin_cost,
        candidate_count=candidate_count,
        field_name="candidate_red_stopping_margin_cost",
    )
    raw_jerk = _candidate_vector(
        candidate_dp_prior_jerk_excess_cost,
        candidate_count=candidate_count,
        field_name="candidate_dp_prior_jerk_excess_cost",
    )
    raw_lateral = _candidate_vector(
        candidate_horizon_lateral_acceleration_cost,
        candidate_count=candidate_count,
        field_name="candidate_horizon_lateral_acceleration_cost",
    )
    target_speed = _candidate_vector(
        candidate_target_speed_mps,
        candidate_count=candidate_count,
        field_name="candidate_target_speed_mps",
    )
    h10_distance = _candidate_vector(
        _perfect_tracker_horizon_distance(perfect_tracker_open_loop, 10),
        candidate_count=candidate_count,
        field_name="h10_distance_m",
    )
    h3_distance = (
        _candidate_vector(
            _perfect_tracker_horizon_distance(perfect_tracker_open_loop, 3),
            candidate_count=candidate_count,
            field_name="h3_distance_m",
        )
        if mode == "h3_h10_guard_005"
        else None
    )
    first_step = (
        _candidate_vector(
            candidate_step_reach,
            candidate_count=candidate_count,
            field_name="candidate_step_reach",
        )
        if mode == "step_h10_guard_005"
        else None
    )
    for field_name, values in (
        ("candidate_union_red_cost", union_red),
        ("candidate_red_stopping_margin_cost", red_stopping),
        ("candidate_dp_prior_jerk_excess_cost", raw_jerk),
        ("candidate_horizon_lateral_acceleration_cost", raw_lateral),
    ):
        if np.any(values < 0.0):
            raise ValueError(f"{field_name} must be nonnegative.")

    budgets = _traffic_light_hybrid_budget(mode)
    stats: dict[str, Any] = {
        "schema_version": "traffic_light_hybrid_postselection_v1",
        "enabled": True,
        "default_off": True,
        "selection_effect": True,
        "online_selector_change": True,
        "future_outcome_leakage": False,
        "classical_benders_claim": False,
        "mode": str(mode),
        "screen_name": f"traffic_light_hybrid_{mode}",
        "baseline_selected_index": selected,
        "selected_index": selected,
        "changed": False,
        "opportunity": False,
        "candidate_count": candidate_count,
        "admissible_candidates": 0,
        "budgets": budgets,
        "requires": {
            "traffic_lights_enabled": True,
            "base_feasible": True,
            "union_red_nondegrading": True,
            "red_stopping_nondegrading": True,
            "raw_lateral_strictly_improving": True,
            "raw_jerk_strictly_improving": True,
            "bounded_progress_loss": True,
            "bounded_h10_distance_loss": True,
            "bounded_target_speed_loss": True,
        },
        "reason": "not_evaluated",
    }
    if not traffic_lights_enabled:
        stats["reason"] = "traffic_lights_disabled"
        return selected, stats
    if selection.used_fallback or not feasible.any():
        stats["reason"] = "fallback_or_no_base_feasible_candidate"
        return selected, stats

    losses: dict[str, np.ndarray] = {
        "dp_reward_progress_loss_m": _loss(progress, selected),
        "h10_distance_loss_m": _loss(h10_distance, selected),
        "target_speed_loss_mps": _loss(target_speed, selected),
    }
    if first_step is not None:
        losses["first_step_loss_m"] = _loss(first_step, selected)
    if h3_distance is not None:
        losses["h3_distance_loss_m"] = _loss(h3_distance, selected)

    admissible = (
        feasible.copy()
        & (union_red <= union_red[selected] + TRAFFIC_LIGHT_HYBRID_TOL)
        & (
            red_stopping
            <= red_stopping[selected] + TRAFFIC_LIGHT_HYBRID_TOL
        )
        & (
            raw_lateral
            < raw_lateral[selected] - TRAFFIC_LIGHT_HYBRID_TOL
        )
        & (raw_jerk < raw_jerk[selected] - TRAFFIC_LIGHT_HYBRID_TOL)
    )
    for budget_name, budget_value in budgets.items():
        admissible &= losses[budget_name] <= float(budget_value) + (
            TRAFFIC_LIGHT_HYBRID_TOL
        )
    admissible[selected] = False
    indices = np.flatnonzero(admissible)
    stats["admissible_candidates"] = int(indices.size)
    stats["opportunity"] = bool(indices.size)
    if not indices.size:
        stats["reason"] = "no_admissible_traffic_light_hybrid_candidate"
        return selected, stats

    def key(candidate_index: int) -> tuple[float, ...]:
        loss_terms = tuple(
            float(losses[budget_name][candidate_index])
            for budget_name in budgets
        )
        return (
            float(raw_lateral[candidate_index]),
            float(raw_jerk[candidate_index]),
            *loss_terms,
            float(scores[candidate_index]),
            float(candidate_index),
        )

    chosen = min((int(index) for index in indices.tolist()), key=key)
    chosen_losses = {
        name: float(values[chosen])
        for name, values in sorted(losses.items())
    }
    stats.update(
        {
            "changed": bool(chosen != selected),
            "reason": "selected_admissible_traffic_light_hybrid_candidate",
            "selected_index": int(chosen),
            "admissible_indices": [int(index) for index in indices.tolist()],
            "losses": chosen_losses,
            "delta": {
                "union_red": float(union_red[chosen] - union_red[selected]),
                "red_stopping": float(
                    red_stopping[chosen] - red_stopping[selected]
                ),
                "raw_lateral": float(
                    raw_lateral[chosen] - raw_lateral[selected]
                ),
                "raw_jerk": float(raw_jerk[chosen] - raw_jerk[selected]),
                "dp_reward_progress_m": float(
                    progress[chosen] - progress[selected]
                ),
                "h10_distance_m": float(
                    h10_distance[chosen] - h10_distance[selected]
                ),
                "target_speed_mps": float(
                    target_speed[chosen] - target_speed[selected]
                ),
            },
        }
    )
    if h3_distance is not None:
        stats["delta"]["h3_distance_m"] = float(
            h3_distance[chosen] - h3_distance[selected]
        )
    if first_step is not None:
        stats["delta"]["first_step_reach_m"] = float(
            first_step[chosen] - first_step[selected]
        )
    return int(chosen), stats


def _evaluation_state(scene: Any, ego_id: str) -> dict[str, Any]:
    ego = scene.get_agent(ego_id)
    route_lanes = np.asarray(ego.route_lanes, dtype=np.float64)
    if route_lanes.ndim == 4 and route_lanes.shape[0] == 1:
        route_lanes = route_lanes[0]
    red_points: list[list[float]] = []
    if route_lanes.ndim == 3 and route_lanes.shape[-1] > 10:
        red_mask = route_lanes[:, :, 10] > 0.5
        valid = np.linalg.norm(route_lanes[:, :, :2], axis=-1) > 0.1
        for point in route_lanes[red_mask & valid]:
            red_points.append(
                [
                    float(point[0]),
                    float(point[1]),
                    float(point[2]),
                    float(point[3]),
                ]
            )
    return {
        "step": None,
        "x": float(ego.current_position[0]),
        "y": float(ego.current_position[1]),
        "heading": float(ego.current_heading),
        "red_route_points": red_points,
    }


def _perfect_tracker_candidate_preprocessing(spawn_config: Any) -> dict[str, Any]:
    enabled = bool(getattr(spawn_config, "sg_smooth_enabled", False))
    return {
        "reference_implementation": (
            "rlvr.grpo_sft_trainer._smooth_trajectory"
        ),
        "shadow_implementation": (
            "scripts.integrations.run_diffusion_planner_camp_replay."
            "_prepare_perfect_tracker_reference_candidates"
        ),
        "application_stage": (
            "replay_after_predict_before_advance_scene_mpc"
        ),
        "savgol_enabled": enabled,
        "savgol_window": (
            int(getattr(spawn_config, "sg_filter_window"))
            if enabled
            else None
        ),
        "savgol_order": (
            int(getattr(spawn_config, "sg_filter_order"))
            if enabled
            else None
        ),
    }


def _prepare_perfect_tracker_reference_candidates(
    candidates: np.ndarray,
    spawn_config: Any,
) -> np.ndarray:
    """Vectorize DP's per-trajectory Savitzky-Golay preprocessing."""
    trajectories = np.asarray(candidates)
    if not bool(getattr(spawn_config, "sg_smooth_enabled", False)):
        return trajectories
    from scipy.signal import savgol_filter

    horizon_steps = int(trajectories.shape[1])
    window = min(int(spawn_config.sg_filter_window), horizon_steps)
    if window % 2 == 0:
        window -= 1
    order = int(spawn_config.sg_filter_order)
    if window < order + 2:
        return trajectories
    smoothed = np.copy(trajectories)
    smoothed[:, :, :4] = savgol_filter(
        trajectories[:, :, :4],
        window,
        order,
        axis=1,
    )
    heading_norm = np.linalg.norm(smoothed[:, :, 2:4], axis=2)
    heading_norm = np.clip(heading_norm, 1e-6, None)
    smoothed[:, :, 2:4] /= heading_norm[:, :, np.newaxis]
    if smoothed.shape != trajectories.shape or not np.all(np.isfinite(smoothed)):
        raise RuntimeError(
            "Diffusion Planner trajectory smoothing returned invalid candidates."
        )
    return smoothed


def _prepare_reward_scoring_candidates(
    candidates: np.ndarray,
    spawn_config: Any,
) -> np.ndarray:
    scored_candidates = np.asarray(candidates, dtype=np.float32).copy()
    if not bool(getattr(spawn_config, "sg_smooth_enabled", False)):
        return scored_candidates
    return _prepare_perfect_tracker_reference_candidates(
        scored_candidates,
        spawn_config,
    )


def _reward_horizon_trajectories(
    full_trajectories: Any,
    reward_horizon_steps: int,
) -> Any:
    return full_trajectories[:, :reward_horizon_steps].contiguous()


def _append_metric_record(
    *,
    replay_module: Any,
    tensor_converter_module: Any,
    scene: Any,
    map_cache: Any,
    model_args: Any,
    prediction: np.ndarray,
    device: str,
    reward_config: Any,
    spawn_config: Any,
    records: list[dict[str, Any]],
) -> None:
    if reward_config is None:
        return
    if map_cache is None:
        raise RuntimeError("Reward scoring requires Diffusion Planner map_cache.")
    data = tensor_converter_module.dump_step_npz(
        scene,
        map_cache,
        future_len=int(model_args.future_len),
        predicted_neighbor_num=int(model_args.predicted_neighbor_num),
    )
    scored_prediction = np.asarray(prediction).copy()
    if bool(getattr(spawn_config, "sg_smooth_enabled", False)):
        scored_prediction = replay_module._sg_smooth_trajectory(
            scored_prediction,
            int(spawn_config.sg_filter_window),
            int(spawn_config.sg_filter_order),
        )
    records.append(
        replay_module._score_step(
            data,
            len(records),
            device,
            reward_config,
            spawn_config,
            prediction=scored_prediction,
        )
    )


def _score_candidate_batch(
    *,
    replay_module: Any,
    tensor_converter_module: Any,
    scene: Any,
    map_cache: Any,
    model_args: Any,
    candidates: np.ndarray,
    device: str,
    reward_config: Any,
    spawn_config: Any,
    reward_horizon_steps: int,
) -> tuple[list[dict[str, Any]], np.ndarray, float, dict[str, float]]:
    if map_cache is None:
        raise RuntimeError("Candidate reward scoring requires Diffusion Planner map_cache.")

    import torch
    from rlvr.reward import compute_red_light_score_batch, compute_reward_batch

    batch_start = time.perf_counter()
    npz_data = tensor_converter_module.dump_step_npz(
        scene,
        map_cache,
        future_len=int(model_args.future_len),
        predicted_neighbor_num=int(model_args.predicted_neighbor_num),
    )
    npz_done = time.perf_counter()

    def _to_tensor(array: np.ndarray) -> torch.Tensor:
        tensor = torch.from_numpy(np.asarray(array)).float().to(device)
        return tensor.unsqueeze(0) if tensor.dim() == 3 else tensor

    reward_data: dict[str, torch.Tensor] = {}
    keys = (
        "lanes",
        "route_lanes",
        "line_strings",
        "ego_shape",
        "neighbor_agents_future",
        "neighbor_agents_past",
        "goal_pose",
    )
    for key in keys:
        if key not in npz_data:
            continue
        array = np.asarray(npz_data[key])
        if key == "goal_pose" and array.shape[-1] == 3:
            yaw = array[..., 2]
            array = np.stack(
                (array[..., 0], array[..., 1], np.cos(yaw), np.sin(yaw)),
                axis=-1,
            )
        reward_data[key] = _to_tensor(array)
    tensor_setup_done = time.perf_counter()

    scored_candidates = _prepare_reward_scoring_candidates(
        candidates,
        spawn_config,
    )
    smoothing_done = time.perf_counter()
    full_trajectories = torch.from_numpy(scored_candidates).float().to(device)
    reward_trajectories = _reward_horizon_trajectories(
        full_trajectories,
        reward_horizon_steps,
    )
    candidate_tensor_done = time.perf_counter()
    reward_compute_start = time.perf_counter()
    with torch.inference_mode():
        raw_reward_breakdowns = compute_reward_batch(
            reward_trajectories,
            reward_data,
            reward_config,
        )
    reward_compute_done = time.perf_counter()
    reward_breakdowns = [
        asdict(breakdown)
        for breakdown in raw_reward_breakdowns
    ]
    reward_postprocess_done = time.perf_counter()
    full_red_start = time.perf_counter()
    with torch.inference_mode():
        full_red_scores = compute_red_light_score_batch(
            full_trajectories,
            reward_data,
            reward_config,
        )
    full_red_cost = np.maximum(
        -full_red_scores.detach().cpu().numpy().astype(np.float64),
        0.0,
    )
    full_red_done = time.perf_counter()
    full_red_latency_ms = (full_red_done - full_red_start) * 1000.0
    latency_breakdown_ms = {
        "latency_ms_reward_npz_dump": (npz_done - batch_start) * 1000.0,
        "latency_ms_reward_tensor_setup": (tensor_setup_done - npz_done) * 1000.0,
        "latency_ms_reward_sg_smoothing": (
            smoothing_done - tensor_setup_done
        )
        * 1000.0,
        "latency_ms_reward_candidate_tensor_transfer": (
            candidate_tensor_done - smoothing_done
        )
        * 1000.0,
        "latency_ms_reward_batch_compute": (
            reward_compute_done - reward_compute_start
        )
        * 1000.0,
        "latency_ms_reward_postprocess": (
            reward_postprocess_done - reward_compute_done
        )
        * 1000.0,
        "latency_ms_reward_full_horizon_red_light": (
            full_red_done - full_red_start
        )
        * 1000.0,
    }
    return (
        reward_breakdowns,
        full_red_cost,
        full_red_latency_ms,
        latency_breakdown_ms,
    )


def _candidate_feasibility_from_rewards(
    rewards: list[dict[str, Any]],
    min_progress_ratio: float,
    min_candidate0_progress_ratio: float | None = None,
) -> tuple[np.ndarray, tuple[tuple[str, ...], ...]]:
    feasible = np.ones(len(rewards), dtype=bool)
    reasons: list[list[str]] = [[] for _ in rewards]

    for idx, reward in enumerate(rewards):
        checks = (
            ("dp_collision", reward.get("collision_step") is not None),
            ("dp_road_border", bool(reward.get("rb_crossing", False))),
            ("dp_lane_crossing", bool(reward.get("lane_crossing", False))),
            ("dp_static_collision", bool(reward.get("static_crossing", False))),
            ("dp_kinematic", bool(reward.get("kinematic_violated", False))),
            ("dp_red_light", float(reward.get("red_light", 0.0)) < -0.5),
        )
        for reason, failed in checks:
            if failed:
                reasons[idx].append(reason)
        feasible[idx] = not reasons[idx]

    safe_indices = np.flatnonzero(feasible)
    if safe_indices.size:
        safe_progress = np.asarray(
            [float(rewards[idx].get("progress", 0.0)) for idx in safe_indices],
            dtype=np.float64,
        )
        best_progress = float(np.max(safe_progress))
        if best_progress > 0.0:
            minimum_progress = best_progress * float(min_progress_ratio)
            for idx in safe_indices:
                if float(rewards[idx].get("progress", 0.0)) < minimum_progress:
                    feasible[idx] = False
                    reasons[idx].append("dp_underprogress")
        if min_candidate0_progress_ratio is not None and rewards:
            candidate0_progress = float(rewards[0].get("progress", 0.0))
            if candidate0_progress > 0.0:
                minimum_candidate0_progress = (
                    candidate0_progress * float(min_candidate0_progress_ratio)
                )
                for idx in safe_indices:
                    if idx == 0:
                        continue
                    if (
                        float(rewards[idx].get("progress", 0.0))
                        < minimum_candidate0_progress
                    ):
                        feasible[idx] = False
                        reasons[idx].append("dp_candidate0_underprogress")

    return feasible, tuple(tuple(row) for row in reasons)


def _install_top1_observer(
    replay_module: Any,
    tensor_converter_module: Any,
    *,
    reward_config: Any,
    spawn_config: Any,
) -> tuple[Any, list[dict[str, Any]], list[dict[str, Any]]]:
    original_predict = replay_module._predict_batch
    metric_records: list[dict[str, Any]] = []
    evaluation_records: list[dict[str, Any]] = []

    def observed_predict(
        model,
        model_args,
        scene,
        agent_ids,
        device,
        map_cache=None,
        return_turn_indicators=False,
        inference_delay=0,
        turn_indicator_keep_bias=0.25,
    ):
        base = original_predict(
            model,
            model_args,
            scene,
            agent_ids,
            device,
            map_cache=map_cache,
            return_turn_indicators=return_turn_indicators,
            inference_delay=inference_delay,
            turn_indicator_keep_bias=turn_indicator_keep_bias,
        )
        ego_id = scene.ego_agent_id
        if ego_id not in agent_ids:
            return base
        predictions = base[0] if return_turn_indicators else base
        state = _evaluation_state(scene, ego_id)
        state["step"] = len(evaluation_records)
        evaluation_records.append(state)
        _append_metric_record(
            replay_module=replay_module,
            tensor_converter_module=tensor_converter_module,
            scene=scene,
            map_cache=map_cache,
            model_args=model_args,
            prediction=predictions[ego_id],
            device=device,
            reward_config=reward_config,
            spawn_config=spawn_config,
            records=metric_records,
        )
        return base

    replay_module._predict_batch = observed_predict
    return original_predict, metric_records, evaluation_records


def _write_microbenchmark_snapshot(
    *,
    output_dir: Path,
    selection_step: int,
    normalized_inputs: dict[str, Any],
    tensor_converter_module: Any,
    scene: Any,
    map_cache: Any,
    model_args: Any,
    candidates: np.ndarray,
    neighbor_predictions: np.ndarray,
    candidate_obstacles: np.ndarray | None,
    context: Any,
    selector: CAMPSelector,
    selection: CAMPSelectionResult,
    scene_features: np.ndarray,
    external_feasible_mask: np.ndarray | None,
    external_infeasibility_reasons: Any,
    candidate_progress: np.ndarray | None,
    candidate_planned_red_light_cost: np.ndarray | None,
    candidate_full_horizon_planned_red_light_cost: np.ndarray | None,
    candidate_red_stopping_margin_cost: np.ndarray,
    candidate_dp_prior_jerk_excess_cost: np.ndarray,
    candidate_generation_contract: dict[str, Any],
    red_route_points: np.ndarray,
    perfect_tracker_current_speed_mps: float,
    perfect_tracker_current_longitudinal_acceleration_mps2: float,
    perfect_tracker_current_acceleration_ego_xy: np.ndarray,
    num_candidates: int,
    noise_scale: float,
    reference_blend_steps: int | None,
    reward_horizon_steps: int,
    outcome_horizon_steps: int,
    spawn_config: Any,
) -> Path:
    """Write a default-off current-tick snapshot for independent profiling."""
    arrays: dict[str, np.ndarray] = {
        "candidates": np.asarray(candidates),
        "neighbor_predictions": np.asarray(neighbor_predictions),
        "candidate_obstacles": (
            np.asarray(candidate_obstacles)
            if candidate_obstacles is not None
            else np.empty((num_candidates, 0, candidates.shape[1], 2))
        ),
        "lane_centerline": np.asarray(context.lane_centerline),
        "static_obstacles": (
            np.asarray(context.static_obstacles)
            if context.static_obstacles is not None
            else np.empty((0, 2))
        ),
        "atom_scales": np.asarray(selector.atom_scales),
        "selection_atoms": np.asarray(selection.atoms),
        "selection_normalized_atoms": np.asarray(selection.normalized_atoms),
        "selection_weights": np.asarray(selection.selection_weights),
        "selection_scores": np.asarray(selection.selection_scores),
        "feasible_mask": np.asarray(selection.feasible_mask),
        "scene_features": np.asarray(scene_features),
        "red_route_points": np.asarray(red_route_points),
        "current_acceleration_ego_xy": np.asarray(
            perfect_tracker_current_acceleration_ego_xy
        ),
        "candidate_red_stopping_margin_cost": np.asarray(
            candidate_red_stopping_margin_cost
        ),
        "candidate_dp_prior_jerk_excess_cost": np.asarray(
            candidate_dp_prior_jerk_excess_cost
        ),
    }
    optional_arrays = {
        "external_feasible_mask": external_feasible_mask,
        "candidate_progress": candidate_progress,
        "candidate_planned_red_light_cost": candidate_planned_red_light_cost,
        "candidate_full_horizon_planned_red_light_cost": (
            candidate_full_horizon_planned_red_light_cost
        ),
    }
    for key, value in optional_arrays.items():
        if value is not None:
            arrays[key] = np.asarray(value)

    model_input_keys = []
    for key, value in normalized_inputs.items():
        if hasattr(value, "detach") and hasattr(value, "cpu"):
            tensor = value.detach().cpu()
            try:
                array = tensor.numpy()
            except TypeError:
                tensor = tensor.float()
                array = tensor.numpy()
            arrays[f"model_input__{key}"] = array
            model_input_keys.append(key)
        elif isinstance(value, np.ndarray):
            arrays[f"model_input__{key}"] = value
            model_input_keys.append(key)

    reward_input_keys = []
    if map_cache is not None:
        reward_inputs = tensor_converter_module.dump_step_npz(
            scene,
            map_cache,
            future_len=int(model_args.future_len),
            predicted_neighbor_num=int(model_args.predicted_neighbor_num),
        )
        for key, value in reward_inputs.items():
            if isinstance(value, np.ndarray):
                arrays[f"reward_input__{key}"] = value
                reward_input_keys.append(key)

    metadata = {
        "format_version": 1,
        "selection_step": int(selection_step),
        "num_candidates": int(num_candidates),
        "candidate_horizon_steps": int(candidates.shape[1]),
        "candidate_dimension": int(candidates.shape[2]),
        "candidate_noise_scale": float(noise_scale),
        "candidate_reference_blend_steps": reference_blend_steps,
        "candidate_generation_contract": candidate_generation_contract,
        "candidate_generation_seed": int(1729 + selection_step),
        "candidate_generation_seed_scope": (
            "microbenchmark_replay_only_not_original_tick_rng"
        ),
        "reward_horizon_steps": int(reward_horizon_steps),
        "outcome_horizon_steps": int(outcome_horizon_steps),
        "dt": float(context.dt),
        "speed_limit": context.speed_limit,
        "desired_speed": context.desired_speed,
        "lane_half_width": float(context.lane_half_width),
        "lane_corridor_buffer": float(context.lane_corridor_buffer),
        "safety_radius": float(context.safety_radius),
        "clearance_soft_margin": float(context.clearance_soft_margin),
        "map_source": str(context.map_source),
        "atom_clip": float(selector.atom_clip),
        "fallback_mode": str(selector.fallback_mode),
        "used_fallback": bool(selection.used_fallback),
        "selected_index": int(selection.selected_index),
        "infeasibility_reasons": [
            list(reasons) for reasons in selection.infeasibility_reasons
        ],
        "external_infeasibility_reasons": (
            None
            if external_infeasibility_reasons is None
            else [
                list(reasons) for reasons in external_infeasibility_reasons
            ]
        ),
        "current_speed_mps": float(perfect_tracker_current_speed_mps),
        "current_longitudinal_acceleration_mps2": float(
            perfect_tracker_current_longitudinal_acceleration_mps2
        ),
        "perfect_tracker_open_loop_horizons": list(
            PERFECT_TRACKER_OPEN_LOOP_HORIZONS
        ),
        "sg_smooth_enabled": bool(
            getattr(spawn_config, "sg_smooth_enabled", False)
        ),
        "sg_filter_window": int(getattr(spawn_config, "sg_filter_window", 0)),
        "sg_filter_order": int(getattr(spawn_config, "sg_filter_order", 0)),
        "model_input_keys": sorted(model_input_keys),
        "reward_input_keys": sorted(reward_input_keys),
        "capture_has_no_selection_effect": True,
    }
    arrays["metadata_json"] = np.asarray(json.dumps(metadata, sort_keys=True))

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"camp_microbenchmark_step_{selection_step:04d}.npz"
    np.savez_compressed(output_path, **arrays)
    return output_path


def _candidate_generation_contract(
    model_args: Any,
    *,
    num_candidates: int,
    noise_scale: float,
    noise_strategy: str,
    reference_blend_steps: int | None,
    guidance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if noise_strategy not in {"iid", "antithetic"}:
        raise ValueError("noise_strategy must be 'iid' or 'antithetic'.")
    future_len = int(model_args.future_len)
    predicted_neighbor_num = int(model_args.predicted_neighbor_num)
    guidance_payload = guidance or {
        "enabled": False,
        "policy": "disabled_for_camp_candidate_generation",
        "config_path": None,
        "config_sha256": None,
        "functions": [],
        "guidance_scale": None,
    }
    return {
        "schema_version": "dp_candidate_generation_contract_v1",
        "model_type": str(getattr(model_args, "diffusion_model_type", "unknown")),
        "future_len": future_len,
        "predicted_neighbor_num": predicted_neighbor_num,
        "num_candidates": int(num_candidates),
        "latent_shape": [
            int(num_candidates),
            1 + predicted_neighbor_num,
            future_len + 1,
            4,
        ],
        "latent_distribution": "standard_normal_scaled",
        "noise_strategy": noise_strategy,
        "latent_pairing": (
            "+z/-z antithetic pairs after deterministic candidate 0; "
            "one unpaired iid draw if stochastic count is odd"
            if noise_strategy == "antithetic"
            else "independent iid draws after deterministic candidate 0"
        ),
        "noise_scale": float(noise_scale),
        "deterministic_first": True,
        "candidate0_latent": "zeros",
        "candidate0_guidance_policy": (
            "full_batch_unguided_forward"
            if bool(guidance_payload.get("enabled", False))
            else "single_unguided_forward"
        ),
        "guided_candidate_indices": (
            [1, int(num_candidates) - 1]
            if bool(guidance_payload.get("enabled", False))
            and int(num_candidates) > 1
            else []
        ),
        "candidate0_preservation_structural": bool(
            guidance_payload.get("enabled", False)
        ),
        "random_seed_scope": "process_global_torch_rng",
        "recorded_tick_seed": None,
        "guidance_enabled": bool(guidance_payload.get("enabled", False)),
        "guidance_policy": str(
            guidance_payload.get("policy", "disabled_for_camp_candidate_generation")
        ),
        "guidance": guidance_payload,
        "dpm_solver_steps": 10,
        "dpm_skip_type": "logSNR",
        "reference_blend_steps": reference_blend_steps,
        "changes_candidate_set": True,
        "changes_camp_score": False,
        "changes_diffusion_planner_weights": False,
    }


def _dp_camp_finite_candidate_contract(
    *,
    selector_mode: str,
    num_candidates: int,
    feasibility_source: str,
    fallback_mode: str,
    atom_clip: float,
) -> dict[str, Any]:
    enabled = selector_mode != "top1"
    return {
        "schema_version": "dp_camp_finite_candidate_contract_v1",
        "enabled": enabled,
        "selector_mode": str(selector_mode),
        "num_candidates": int(num_candidates) if enabled else 1,
        "candidate_set": (
            "fixed current-tick Diffusion Planner candidate tensor before "
            "CAMP scoring"
            if enabled
            else "upstream Diffusion Planner top-1 only"
        ),
        "score": "a_ik^T w" if enabled else None,
        "selection_rule": (
            "argmin over finite feasible candidates by CAMP selection score"
            if enabled
            else "upstream Diffusion Planner selected trajectory"
        ),
        "atom_contract": {
            "fixed_before_scoring": bool(enabled),
            "finite": bool(enabled),
            "nonnegative_after_normalization": bool(enabled),
            "clip": float(atom_clip) if enabled else None,
        },
        "weight_contract": {
            "simplex_weights_expected": bool(enabled),
            "affine_score_in_weights": bool(enabled),
        },
        "feasibility_source": str(feasibility_source) if enabled else None,
        "fail_closed_policy": (
            "if the finite feasible set is empty, selection stays inside the "
            "same current-tick candidate set and uses the configured fallback "
            "mode"
            if enabled
            else None
        ),
        "fallback_mode": str(fallback_mode) if enabled else None,
        "training_claim": (
            "finite-candidate generalized Benders-style cutting-plane "
            "training applies only to logged fixed candidates with fixed atoms, "
            "oracle labels, and nonnegative margins"
            if enabled
            else None
        ),
        "classical_benders_claim": False,
        "excluded_from_subproblem": [
            "Diffusion Planner neural sampler",
            "Savitzky-Golay smoothing",
            "postprocess_reference",
            "PerfectTracker state transition",
            "closed-loop simulator future states",
            "route and traffic-light geometry",
        ],
    }


def _copy_replay_contract_metadata_to_validation(
    validation: dict[str, Any],
    replay_summary: dict[str, Any],
) -> None:
    for key in (
        "candidate_generation_contract",
        "dp_camp_finite_candidate_contract",
    ):
        validation[key] = replay_summary.get(key)


def _raw_candidate_prefix_payload(
    candidates: np.ndarray,
    steps: int,
) -> dict[str, Any]:
    if steps < 0:
        raise ValueError("raw candidate prefix logging steps must be non-negative.")
    if steps == 0:
        return {}
    raw_candidates = np.asarray(candidates)
    if raw_candidates.ndim != 3:
        raise ValueError("raw candidate prefix logging expects a rank-3 array.")
    effective_steps = min(int(steps), int(raw_candidates.shape[1]))
    return {
        "candidate_raw_trajectory_prefix_steps": effective_steps,
        "candidate_raw_trajectory_prefix": (
            raw_candidates[:, :effective_steps, :].tolist()
        ),
    }


def _lower_union_red_donor_indices(
    union_red_cost: np.ndarray,
    selected_index: int,
) -> np.ndarray:
    union = np.asarray(union_red_cost, dtype=np.float64).reshape(-1)
    selected = int(selected_index)
    if selected < 0 or selected >= union.size:
        raise ValueError("selected_index is out of range.")
    if not np.all(np.isfinite(union)) or np.any(union < 0.0):
        raise ValueError("union_red_cost must be finite and nonnegative.")
    indices = np.arange(union.size, dtype=np.int64)
    nonselected = indices[indices != selected]
    return nonselected[union[nonselected] < union[selected] - 1e-12]


def _evaluate_splice_shadow_rule(
    *,
    replay_module: Any,
    tensor_converter_module: Any,
    scene: Any,
    map_cache: Any,
    model_args: Any,
    candidates: np.ndarray,
    baseline_selected_index: int,
    candidate_rewards: list[dict[str, Any]],
    candidate_union_red_cost: np.ndarray,
    device: str,
    reward_config: Any,
    spawn_config: Any,
    reward_horizon_steps: int,
    anchor_steps: int,
    blend_steps: int,
    heading_mode: str,
    progress_loss_budget_m: float,
    smoothness_loss_budget: float,
) -> dict[str, Any]:
    start = time.perf_counter()
    donor_indices = _lower_union_red_donor_indices(
        candidate_union_red_cost,
        baseline_selected_index,
    )
    config = {
        "schema_version": "splice_shadow_rule_v1",
        "enabled": True,
        "default_off": True,
        "selection_effect": False,
        "online_selector_change": False,
        "donor_pool": "lower_logged_union_red",
        "anchor_steps": int(anchor_steps),
        "blend_steps": int(blend_steps),
        "heading_mode": str(heading_mode),
        "budget": {
            "progress_loss_m": float(progress_loss_budget_m),
            "smoothness_loss": float(smoothness_loss_budget),
        },
        "baseline_selected_index": int(baseline_selected_index),
        "donor_indices": [int(index) for index in donor_indices.tolist()],
        "donor_count": int(donor_indices.size),
    }
    selected_union_red = float(
        np.asarray(candidate_union_red_cost, dtype=np.float64)[
            int(baseline_selected_index)
        ]
    )
    selected_progress = float(
        candidate_rewards[int(baseline_selected_index)]["progress"]
    )
    selected_smoothness = float(
        candidate_rewards[int(baseline_selected_index)]["smoothness"]
    )
    if not donor_indices.size:
        rule = fixed_candidate_shadow_rule(
            union_red=np.empty(0, dtype=np.float64),
            progress=np.empty(0, dtype=np.float64),
            smoothness=np.empty(0, dtype=np.float64),
            hard_feasible=np.empty(0, dtype=bool),
            selected_union_red=selected_union_red,
            selected_progress=selected_progress,
            selected_smoothness=selected_smoothness,
            enabled=True,
            progress_loss_budget_m=progress_loss_budget_m,
            smoothness_loss_budget=smoothness_loss_budget,
        )
        config.update(rule)
        config["latency_ms"] = (time.perf_counter() - start) * 1000.0
        return config

    transformed = build_splice_candidates(
        np.asarray(candidates, dtype=np.float64),
        selected_index=int(baseline_selected_index),
        donor_indices=donor_indices,
        anchor_steps=int(anchor_steps),
        blend_steps=int(blend_steps),
        heading_mode=str(heading_mode),
    )
    (
        transformed_rewards,
        transformed_full_red_cost,
        full_red_latency_ms,
        _transformed_reward_latency_breakdown_ms,
    ) = (
        _score_candidate_batch(
            replay_module=replay_module,
            tensor_converter_module=tensor_converter_module,
            scene=scene,
            map_cache=map_cache,
            model_args=model_args,
            candidates=transformed,
            device=device,
            reward_config=reward_config,
            spawn_config=spawn_config,
            reward_horizon_steps=reward_horizon_steps,
        )
    )
    transformed_near_red_cost = np.asarray(
        [
            max(-float(reward.get("red_light", 0.0)), 0.0)
            for reward in transformed_rewards
        ],
        dtype=np.float64,
    )
    transformed_union_red_cost = np.maximum(
        transformed_near_red_cost,
        transformed_full_red_cost,
    )
    transformed_hard_feasible, transformed_hard_reasons = reward_hard_feasibility(
        transformed_rewards
    )
    transformed_progress = reward_metric_vector(transformed_rewards, "progress")
    transformed_smoothness = reward_metric_vector(
        transformed_rewards,
        "smoothness",
    )
    rule = fixed_candidate_shadow_rule(
        union_red=transformed_union_red_cost,
        progress=transformed_progress,
        smoothness=transformed_smoothness,
        hard_feasible=transformed_hard_feasible,
        selected_union_red=selected_union_red,
        selected_progress=selected_progress,
        selected_smoothness=selected_smoothness,
        enabled=True,
        progress_loss_budget_m=progress_loss_budget_m,
        smoothness_loss_budget=smoothness_loss_budget,
    )
    chosen = rule["chosen_transformed_index"]
    lower_union_red = transformed_union_red_cost < selected_union_red - 1e-12
    config.update(
        {
            "transform_count": int(transformed.shape[0]),
            "lower_union_red_count": int(np.sum(lower_union_red)),
            "hard_feasible_count": int(np.sum(transformed_hard_feasible)),
            "lower_union_red_hard_feasible_count": int(
                np.sum(lower_union_red & transformed_hard_feasible)
            ),
            "hard_infeasible_reason_counts": reason_counts(
                transformed_hard_reasons,
                ~transformed_hard_feasible,
            ),
            "lower_union_red_hard_infeasible_reason_counts": reason_counts(
                transformed_hard_reasons,
                lower_union_red & ~transformed_hard_feasible,
            ),
            "full_red_latency_ms": float(full_red_latency_ms),
            "chosen_donor_index": (
                int(donor_indices[int(chosen)]) if chosen is not None else None
            ),
        }
    )
    config.update(rule)
    config["latency_ms"] = (time.perf_counter() - start) * 1000.0
    return config


def _summarize_splice_shadow_rule_records(
    records: list[dict[str, Any]] | None,
    *,
    enabled: bool,
    anchor_steps: int,
    blend_steps: int,
    heading_mode: str,
    progress_loss_budget_m: float,
    smoothness_loss_budget: float,
) -> dict[str, Any] | None:
    if records is None:
        return None
    summary: dict[str, Any] = {
        "enabled": bool(enabled),
        "default_off": True,
        "selection_effect": False,
        "online_selector_change": False,
        "schema_version": "splice_shadow_rule_v1",
        "donor_pool": "lower_logged_union_red",
        "anchor_steps": int(anchor_steps),
        "blend_steps": int(blend_steps),
        "heading_mode": str(heading_mode),
        "budget": {
            "progress_loss_m": float(progress_loss_budget_m),
            "smoothness_loss": float(smoothness_loss_budget),
        },
        "field": "splice_shadow_rule",
    }
    if not enabled:
        return summary

    shadows = [
        record.get("splice_shadow_rule")
        for record in records
        if record.get("splice_shadow_rule") is not None
    ]
    summary["records"] = len(shadows)
    summary["changed_records"] = int(
        sum(int(bool(shadow["changed"])) for shadow in shadows)
    )
    summary["admissible_count"] = int(
        sum(int(shadow["admissible_count"]) for shadow in shadows)
    )
    summary["reason_counts"] = _sum_reason_counts(
        {str(shadow["reason"]): 1} for shadow in shadows
    )
    summary["hard_infeasible_reason_counts"] = _sum_reason_counts(
        shadow.get("hard_infeasible_reason_counts", {}) for shadow in shadows
    )
    summary["lower_union_red_hard_infeasible_reason_counts"] = _sum_reason_counts(
        shadow.get("lower_union_red_hard_infeasible_reason_counts", {})
        for shadow in shadows
    )
    summary["latency_ms"] = _summary(
        [
            float(record["latency_ms_splice_shadow_rule"])
            for record in records
            if record.get("latency_ms_splice_shadow_rule") is not None
        ]
    )
    summary["chosen_union_red"] = _summary(
        [
            float(shadow["chosen_union_red"])
            for shadow in shadows
            if shadow.get("chosen_union_red") is not None
        ]
    )
    summary["chosen_progress_loss_m"] = _summary(
        [
            float(shadow["chosen_progress_loss_m"])
            for shadow in shadows
            if shadow.get("chosen_progress_loss_m") is not None
        ]
    )
    summary["chosen_smoothness_loss"] = _summary(
        [
            float(shadow["chosen_smoothness_loss"])
            for shadow in shadows
            if shadow.get("chosen_smoothness_loss") is not None
        ]
    )
    return summary


def _summarize_traffic_light_hybrid_postselection_records(
    records: list[dict[str, Any]] | None,
    *,
    mode: str,
) -> dict[str, Any] | None:
    if records is None:
        return None
    enabled = mode != "off"
    summary: dict[str, Any] = {
        "enabled": bool(enabled),
        "default_off": True,
        "selection_effect": bool(enabled),
        "online_selector_change": bool(enabled),
        "schema_version": "traffic_light_hybrid_postselection_v1",
        "mode": str(mode),
        "field": "traffic_light_hybrid_postselection",
        "future_outcome_leakage": False,
        "classical_benders_claim": False,
        "budgets": (
            _traffic_light_hybrid_budget(mode) if enabled else None
        ),
    }
    if not enabled:
        return summary

    posts = [
        record.get("traffic_light_hybrid_postselection")
        for record in records
        if record.get("traffic_light_hybrid_postselection") is not None
    ]
    summary["records"] = len(posts)
    summary["changed_records"] = int(
        sum(int(bool(post["changed"])) for post in posts)
    )
    summary["opportunity_records"] = int(
        sum(int(bool(post["opportunity"])) for post in posts)
    )
    summary["admissible_candidates"] = int(
        sum(int(post["admissible_candidates"]) for post in posts)
    )
    summary["reason_counts"] = _sum_reason_counts(
        {str(post["reason"]): 1} for post in posts
    )
    summary["latency_ms"] = _summary(
        [
            float(record["latency_ms_traffic_light_hybrid_postselection"])
            for record in records
            if record.get("latency_ms_traffic_light_hybrid_postselection")
            is not None
        ]
    )
    changed_posts = [post for post in posts if bool(post["changed"])]
    loss_names = sorted(
        {
            loss_name
            for post in changed_posts
            for loss_name in post.get("losses", {})
        }
    )
    summary["changed_loss_summary"] = {
        loss_name: _summary(
            [
                float(post["losses"][loss_name])
                for post in changed_posts
                if loss_name in post.get("losses", {})
            ]
        )
        for loss_name in loss_names
    }
    delta_names = sorted(
        {
            delta_name
            for post in changed_posts
            for delta_name in post.get("delta", {})
        }
    )
    summary["changed_delta_summary"] = {
        delta_name: _summary(
            [
                float(post["delta"][delta_name])
                for post in changed_posts
                if delta_name in post.get("delta", {})
            ]
        )
        for delta_name in delta_names
    }
    return summary


def _summary(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"mean": None, "max": None}
    arr = np.asarray(values, dtype=np.float64)
    return {"mean": float(np.mean(arr)), "max": float(np.max(arr))}


def _sum_reason_counts(rows: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        for reason, count in row.items():
            counts[reason] = counts.get(reason, 0) + int(count)
    return dict(sorted(counts.items()))


def _install_camp_predictor(
    replay_module: Any,
    tensor_converter_module: Any,
    selector: CAMPSelector,
    *,
    num_candidates: int,
    noise_scale: float,
    reference_blend_steps: int | None,
    candidate_generation_contract: dict[str, Any],
    safety_radius: float,
    clearance_margin: float,
    lane_corridor_buffer: float,
    feasibility_source: str,
    min_progress_ratio: float,
    min_candidate0_progress_ratio: float | None,
    min_candidate0_route_progress_ratio: float | None,
    shadow_route_progress: bool,
    shadow_obstacle_clearance: bool,
    shadow_obstacle_clearance_exact_obb: bool,
    min_candidate0_step_reach_ratio: float | None,
    candidate0_step_reach_preserve_feasible: bool,
    lexicographic_progress_epsilon_m: float | None,
    lexicographic_red_epsilon: float,
    lexicographic_jerk_epsilon: float,
    lexicographic_lateral_epsilon: float,
    perfect_tracker_command_postselection: bool,
    traffic_light_hybrid_postselection_mode: str,
    underprogress_relaxation: bool,
    underprogress_progress_loss_budget_m: float,
    underprogress_h3_distance_loss_budget_m: float,
    underprogress_lateral_limit_mps2: float,
    reward_horizon_steps: int,
    collect_closed_loop_outcomes: bool,
    outcome_horizon_steps: int,
    outcome_weights: dict[str, float],
    near_miss_threshold_m: float,
    ego_length: float,
    ego_width: float,
    ego_wheelbase: float,
    reward_config: Any,
    spawn_config: Any,
    route_centerline: np.ndarray,
    observable_state_logging: bool,
    observable_state_support_steps: int,
    observable_state_traffic_light_steps: int,
    observable_state_turn_steps: int,
    red_route_vector_logging: bool,
    progress_support_logging: bool,
    progress_support_steps: int,
    progress_support_dt_s: float,
    lane_hard_violation_support_logging: bool,
    lane_hard_violation_support_steps: int,
    lane_hard_violation_support_dt_s: float,
    lane_hard_violation_corridor_half_width_m: float,
    lane_hard_violation_lateral_rate_budget_mps: float,
    progress_lane_hard_context_logging: bool,
    progress_lane_hard_context_steps: int,
    progress_lane_hard_context_dt_s: float,
    progress_lane_hard_context_corridor_half_width_m: float,
    progress_lane_hard_context_corridor_safety_margin_m: float,
    turn_logit_payload_logging: bool,
    non_turn_logit_interaction_payload_logging: bool,
    external_context_payload_logging: bool,
    external_context_payload_steps: int,
    external_context_payload_dt_s: float,
    temporal_consistency_payload_logging: bool,
    temporal_consistency_payload_steps: int,
    temporal_consistency_payload_dt_s: float,
    temporal_consistency_payload_elapsed_steps: int,
    temporal_consistency_payload_min_overlap_steps: int,
    microbenchmark_snapshot_dir: Path | None,
    microbenchmark_snapshot_steps: tuple[int, ...],
    raw_candidate_prefix_steps: int,
    splice_shadow_rule: bool,
    splice_shadow_anchor_steps: int,
    splice_shadow_blend_steps: int,
    splice_shadow_heading_mode: str,
    splice_shadow_progress_loss_budget_m: float,
    splice_shadow_smoothness_loss_budget: float,
) -> tuple[
    Any,
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    original_predict = replay_module._predict_batch
    records: list[dict[str, Any]] = []
    metric_records: list[dict[str, Any]] = []
    evaluation_records: list[dict[str, Any]] = []
    previous_selected_plan_memory: np.ndarray | None = None

    def camp_predict(
        model,
        model_args,
        scene,
        agent_ids,
        device,
        map_cache=None,
        return_turn_indicators=False,
        inference_delay=0,
        turn_indicator_keep_bias=0.25,
    ):
        nonlocal previous_selected_plan_memory
        base = original_predict(
            model,
            model_args,
            scene,
            agent_ids,
            device,
            map_cache=map_cache,
            return_turn_indicators=return_turn_indicators,
            inference_delay=inference_delay,
            turn_indicator_keep_bias=turn_indicator_keep_bias,
        )
        if return_turn_indicators:
            predictions, turn_indicators = base
        else:
            predictions = base
            turn_indicators = None

        ego_id = scene.ego_agent_id
        if ego_id not in agent_ids:
            return base

        inputs = tensor_converter_module.to_model_tensors(
            scene,
            ego_id,
            model_args,
            device,
            map_cache=map_cache,
            inference_delay=inference_delay,
        )
        scene_features = extract_dp_scene_features(inputs)
        start = time.perf_counter()
        candidates, neighbor_predictions, turn_logits = generate_candidate_trajectories(
            model,
            model_args,
            inputs,
            num_candidates=num_candidates,
            noise_scale=noise_scale,
            deterministic_first=True,
            reference_blend_steps=reference_blend_steps,
            guidance_policy=(
                "preserve_candidate0"
                if candidate_generation_contract.get("guidance_enabled")
                else "disabled"
            ),
            noise_strategy=str(candidate_generation_contract["noise_strategy"]),
        )
        candidate_generation_done = time.perf_counter()
        dp_prior_deviation_start = time.perf_counter()
        candidate_dp_prior_deviation_cost = compute_dp_prior_deviation_costs(
            candidates
        )
        dp_prior_deviation_done = time.perf_counter()
        shadow_dp_prior_deviation_latency_ms = (
            dp_prior_deviation_done - dp_prior_deviation_start
        ) * 1000.0
        dp_prior_comfort_start = time.perf_counter()
        (
            candidate_dp_prior_jerk_excess_cost,
            candidate_dp_prior_acceleration_excess_cost,
        ) = compute_dp_prior_comfort_excess_costs(
            candidates,
            float(getattr(scene, "dt", 0.1)),
            horizon_steps=outcome_horizon_steps,
        )
        dp_prior_comfort_horizon_steps = min(
            outcome_horizon_steps,
            int(candidates.shape[1]),
        )
        dp_prior_comfort_done = time.perf_counter()
        shadow_dp_prior_comfort_excess_latency_ms = (
            dp_prior_comfort_done - dp_prior_comfort_start
        ) * 1000.0
        lateral_comfort_start = time.perf_counter()
        (
            candidate_horizon_lateral_acceleration_cost,
            candidate_dp_prior_lateral_acceleration_excess_cost,
            candidate_horizon_yaw_rate_cost,
            candidate_dp_prior_yaw_rate_excess_cost,
        ) = compute_lateral_comfort_shadow_costs(
            candidates,
            float(getattr(scene, "dt", 0.1)),
            horizon_steps=outcome_horizon_steps,
        )
        lateral_comfort_horizon_steps = min(
            outcome_horizon_steps,
            int(candidates.shape[1]),
        )
        lateral_comfort_done = time.perf_counter()
        shadow_lateral_comfort_latency_ms = (
            lateral_comfort_done - lateral_comfort_start
        ) * 1000.0
        context = build_context_from_scene(
            scene,
            ego_id,
            safety_radius=safety_radius,
            clearance_soft_margin=clearance_margin,
            lane_corridor_buffer=lane_corridor_buffer,
        )
        obstacles = _candidate_obstacles(
            scene,
            ego_id,
            neighbor_predictions,
            replay_module.SceneNPCManager.is_static_npc,
        )
        context_and_obstacles_done = time.perf_counter()
        candidate_obstacle_clearance = None
        shadow_obstacle_clearance_latency_ms = 0.0
        if shadow_obstacle_clearance:
            obstacle_clearance_start = time.perf_counter()
            candidate_obstacle_clearance = (
                compute_candidate_obstacle_clearance_diagnostics(
                    candidates,
                    context,
                    candidate_obstacles=obstacles,
                    horizon_steps=outcome_horizon_steps,
                    near_miss_threshold_m=near_miss_threshold_m,
                    evaluate_exact_obb=shadow_obstacle_clearance_exact_obb,
                    ego_length=ego_length,
                    ego_width=ego_width,
                    ego_wheelbase=ego_wheelbase,
                )
            )
            shadow_obstacle_clearance_latency_ms = (
                time.perf_counter() - obstacle_clearance_start
            ) * 1000.0
        candidate_rewards = None
        candidate_outcomes = None
        candidate_progress = None
        candidate_full_horizon_planned_red_light_cost = None
        candidate_horizon_union_planned_red_light_cost = None
        full_horizon_red_light_latency_ms = 0.0
        reward_latency_breakdown_ms = {
            "latency_ms_reward_npz_dump": 0.0,
            "latency_ms_reward_tensor_setup": 0.0,
            "latency_ms_reward_sg_smoothing": 0.0,
            "latency_ms_reward_candidate_tensor_transfer": 0.0,
            "latency_ms_reward_batch_compute": 0.0,
            "latency_ms_reward_postprocess": 0.0,
            "latency_ms_reward_full_horizon_red_light": 0.0,
            "latency_ms_reward_red_route_points": 0.0,
            "latency_ms_reward_feasibility": 0.0,
            "latency_ms_reward_field_extraction": 0.0,
            "latency_ms_reward_step_reach_guard": 0.0,
            "latency_ms_reward_route_progress": 0.0,
            "latency_ms_reward_route_progress_guard": 0.0,
            "latency_ms_reward_lexicographic_filter": 0.0,
        }
        candidate_route_progress = None
        candidate_step_reach = _candidate_step_reach(candidates)
        perfect_tracker_command_start = time.perf_counter()
        ego_agent = scene.get_agent(ego_id)
        (
            perfect_tracker_current_speed_mps,
            perfect_tracker_current_longitudinal_acceleration_mps2,
        ) = _current_perfect_tracker_state(ego_agent)
        perfect_tracker_current_acceleration_ego_xy = (
            _current_acceleration_ego_xy(
                ego_agent,
                float(getattr(scene, "dt", 0.1)),
            )
        )
        perfect_tracker_reference_candidates = (
            _prepare_perfect_tracker_reference_candidates(
                candidates,
                spawn_config,
            )
        )
        perfect_tracker_command = compute_perfect_tracker_command_diagnostics(
            perfect_tracker_reference_candidates,
            dt=float(getattr(scene, "dt", 0.1)),
            current_speed_mps=perfect_tracker_current_speed_mps,
            current_longitudinal_acceleration_mps2=(
                perfect_tracker_current_longitudinal_acceleration_mps2
            ),
        )
        perfect_tracker_command_done = time.perf_counter()
        shadow_perfect_tracker_command_latency_ms = (
            perfect_tracker_command_done - perfect_tracker_command_start
        ) * 1000.0
        if candidates.shape[1] < PERFECT_TRACKER_OPEN_LOOP_HORIZONS[-1]:
            raise RuntimeError(
                "PerfectTracker open-loop shadow requires at least "
                f"{PERFECT_TRACKER_OPEN_LOOP_HORIZONS[-1]} candidate steps."
            )
        perfect_tracker_open_loop_start = time.perf_counter()
        perfect_tracker_open_loop = (
            compute_perfect_tracker_open_loop_rollout_diagnostics(
                perfect_tracker_command["postprocessed_reference"][
                    :, : PERFECT_TRACKER_OPEN_LOOP_HORIZONS[-1]
                ],
                postprocessed_tail_reference_xy=perfect_tracker_command[
                    "postprocessed_tail_reference_xy"
                ],
                full_horizon_steps=int(candidates.shape[1]),
                dt=float(getattr(scene, "dt", 0.1)),
                current_speed_mps=perfect_tracker_current_speed_mps,
                current_acceleration_ego_xy=(
                    perfect_tracker_current_acceleration_ego_xy
                ),
                horizons=PERFECT_TRACKER_OPEN_LOOP_HORIZONS,
            )
        )
        perfect_tracker_open_loop_done = time.perf_counter()
        shadow_perfect_tracker_open_loop_latency_ms = (
            perfect_tracker_open_loop_done - perfect_tracker_open_loop_start
        ) * 1000.0
        candidate_step_reach_guard_relaxed = False
        lexicographic_stage_counts = None
        candidate_planned_red_light_cost = None
        reward_red_route_points_start = time.perf_counter()
        red_route_points = red_route_points_from_scene(scene, ego_id)
        reward_latency_breakdown_ms["latency_ms_reward_red_route_points"] = (
            time.perf_counter() - reward_red_route_points_start
        ) * 1000.0
        observable_state_logging_payload = None
        observable_state_latency_ms = {
            key: 0.0 for key in OBSERVABLE_STATE_LATENCY_KEYS
        }
        red_route_vector_logging_payload = None
        red_route_vector_latency_ms = 0.0
        progress_support_logging_payload = None
        progress_support_latency_ms = {
            key: 0.0 for key in PROGRESS_SUPPORT_LATENCY_KEYS
        }
        lane_hard_violation_support_logging_payload = None
        lane_hard_violation_support_latency_ms = {
            key: 0.0 for key in LANE_HARD_VIOLATION_SUPPORT_LATENCY_KEYS
        }
        progress_lane_hard_context_logging_payload = None
        progress_lane_hard_context_latency_ms = {
            key: 0.0 for key in PROGRESS_LANE_HARD_CONTEXT_LATENCY_KEYS
        }
        turn_logit_payload_logging_payload = None
        turn_logit_payload_latency_ms = {
            key: 0.0 for key in TURN_LOGIT_PAYLOAD_LATENCY_KEYS
        }
        non_turn_logit_interaction_payload_logging_payload = None
        non_turn_logit_interaction_payload_latency_ms = {
            key: 0.0 for key in NON_TURN_LOGIT_INTERACTION_PAYLOAD_LATENCY_KEYS
        }
        external_context_payload_logging_payload = None
        external_context_payload_latency_ms = {
            key: 0.0 for key in EXTERNAL_CONTEXT_PAYLOAD_LATENCY_KEYS
        }
        temporal_consistency_payload_logging_payload = None
        temporal_consistency_payload_latency_ms = {
            key: 0.0 for key in TEMPORAL_CONSISTENCY_PAYLOAD_LATENCY_KEYS
        }
        route_centerline_ego = None
        if (
            observable_state_logging
            or progress_support_logging
            or lane_hard_violation_support_logging
            or progress_lane_hard_context_logging
            or non_turn_logit_interaction_payload_logging
            or external_context_payload_logging
        ):
            route_centerline_ego = _ego_frame_xy(
                route_centerline,
                np.asarray(ego_agent.current_position, dtype=np.float64),
                float(ego_agent.current_heading),
            )
        if observable_state_logging:
            observable_candidate_obstacle_clearance = candidate_obstacle_clearance
            observable_neighbor_latency_ms = 0.0
            if observable_candidate_obstacle_clearance is None:
                observable_clearance_start = time.perf_counter()
                observable_candidate_obstacle_clearance = (
                    compute_candidate_obstacle_clearance_diagnostics(
                        candidates,
                        context,
                        candidate_obstacles=obstacles,
                        horizon_steps=outcome_horizon_steps,
                        near_miss_threshold_m=near_miss_threshold_m,
                        evaluate_exact_obb=False,
                        ego_length=ego_length,
                        ego_width=ego_width,
                        ego_wheelbase=ego_wheelbase,
                    )
                )
                observable_neighbor_latency_ms = (
                    time.perf_counter() - observable_clearance_start
                ) * 1000.0
            observable_state_logging_payload = _observable_state_logging_payload(
                candidates=candidates,
                route_centerline_ego=route_centerline_ego,
                red_route_points=red_route_points,
                candidate_obstacle_clearance=(
                    observable_candidate_obstacle_clearance
                ),
                support_steps=observable_state_support_steps,
                traffic_light_steps=observable_state_traffic_light_steps,
                turn_steps=observable_state_turn_steps,
                neighbor_clearance_latency_ms=observable_neighbor_latency_ms,
            )
            observable_state_latency_ms = observable_state_logging_payload[
                "latency_ms"
            ]
        if red_route_vector_logging:
            red_vector_start = time.perf_counter()
            red_route_vector_logging_payload = _red_route_vector_logging_payload(
                candidates=candidates,
                red_route_points=red_route_points,
                traffic_light_steps=observable_state_traffic_light_steps,
            )
            red_route_vector_latency_ms = (
                time.perf_counter() - red_vector_start
            ) * 1000.0
            red_route_vector_logging_payload["latency_ms"][
                "latency_ms_red_route_vector_logging"
            ] = red_route_vector_latency_ms
        if progress_support_logging:
            progress_support_logging_payload = (
                build_progress_support_logging_payload(
                    candidates=candidates,
                    route_centerline_ego=route_centerline_ego,
                    support_steps=progress_support_steps,
                    dt_s=progress_support_dt_s,
                )
            )
            progress_support_latency_ms = progress_support_logging_payload[
                "latency_ms"
            ]
        if lane_hard_violation_support_logging:
            lane_hard_violation_support_logging_payload = (
                build_lane_hard_violation_support_logging_payload(
                    candidates=candidates,
                    route_centerline_ego=route_centerline_ego,
                    support_steps=lane_hard_violation_support_steps,
                    dt_s=lane_hard_violation_support_dt_s,
                    corridor_half_width_m=(
                        lane_hard_violation_corridor_half_width_m
                    ),
                    lateral_error_rate_budget_mps=(
                        lane_hard_violation_lateral_rate_budget_mps
                    ),
                )
            )
            lane_hard_violation_support_latency_ms = (
                lane_hard_violation_support_logging_payload["latency_ms"]
            )
        if progress_lane_hard_context_logging:
            progress_lane_hard_context_logging_payload = (
                build_progress_lane_hard_context_logging_payload(
                    candidates=candidates,
                    route_centerline_ego=route_centerline_ego,
                    support_steps=progress_lane_hard_context_steps,
                    dt_s=progress_lane_hard_context_dt_s,
                    corridor_half_width_m=(
                        progress_lane_hard_context_corridor_half_width_m
                    ),
                    corridor_safety_margin_m=(
                        progress_lane_hard_context_corridor_safety_margin_m
                    ),
                )
            )
            progress_lane_hard_context_latency_ms = (
                progress_lane_hard_context_logging_payload["latency_ms"]
            )
        if turn_logit_payload_logging:
            turn_logit_payload_logging_payload = build_turn_logit_payload(
                turn_logits=turn_logits,
                candidate_count=int(candidates.shape[0]),
            )
            turn_logit_payload_latency_ms = (
                turn_logit_payload_logging_payload["latency_ms"]
            )
        external_feasible_mask = None
        external_infeasibility_reasons = None
        if feasibility_source == "dp_reward":
            (
                candidate_rewards,
                candidate_full_horizon_planned_red_light_cost,
                full_horizon_red_light_latency_ms,
                reward_batch_latency_breakdown_ms,
            ) = _score_candidate_batch(
                replay_module=replay_module,
                tensor_converter_module=tensor_converter_module,
                scene=scene,
                map_cache=map_cache,
                model_args=model_args,
                candidates=candidates,
                device=device,
                reward_config=reward_config,
                spawn_config=spawn_config,
                reward_horizon_steps=reward_horizon_steps,
            )
            reward_latency_breakdown_ms.update(reward_batch_latency_breakdown_ms)
            reward_feasibility_start = time.perf_counter()
            (
                external_feasible_mask,
                external_infeasibility_reasons,
            ) = _candidate_feasibility_from_rewards(
                candidate_rewards,
                min_progress_ratio,
                min_candidate0_progress_ratio,
            )
            reward_latency_breakdown_ms["latency_ms_reward_feasibility"] = (
                time.perf_counter() - reward_feasibility_start
            ) * 1000.0
            reward_field_extraction_start = time.perf_counter()
            candidate_progress = np.asarray(
                [reward["progress"] for reward in candidate_rewards],
                dtype=np.float64,
            )
            candidate_planned_red_light_cost = np.asarray(
                [max(-float(reward.get("red_light", 0.0)), 0.0) for reward in candidate_rewards],
                dtype=np.float64,
            )
            candidate_horizon_union_planned_red_light_cost = np.maximum(
                candidate_planned_red_light_cost,
                candidate_full_horizon_planned_red_light_cost,
            )
            reward_latency_breakdown_ms["latency_ms_reward_field_extraction"] = (
                time.perf_counter() - reward_field_extraction_start
            ) * 1000.0
        if min_candidate0_step_reach_ratio is not None:
            reward_step_reach_guard_start = time.perf_counter()
            (
                external_feasible_mask,
                external_infeasibility_reasons,
                candidate_step_reach_guard_relaxed,
            ) = _apply_candidate0_step_reach_guard(
                external_feasible_mask,
                external_infeasibility_reasons,
                candidate_step_reach,
                min_candidate0_step_reach_ratio,
                preserve_any_feasible=candidate0_step_reach_preserve_feasible,
            )
            reward_latency_breakdown_ms["latency_ms_reward_step_reach_guard"] = (
                time.perf_counter() - reward_step_reach_guard_start
            ) * 1000.0
        if (
            min_candidate0_route_progress_ratio is not None
            or shadow_route_progress
            or non_turn_logit_interaction_payload_logging
        ):
            reward_route_progress_start = time.perf_counter()
            route_centerline_ego = _ego_frame_xy(
                route_centerline,
                np.asarray(ego_agent.current_position, dtype=np.float64),
                float(ego_agent.current_heading),
            )
            route_horizon = min(reward_horizon_steps, int(candidates.shape[1]))
            candidate_route_progress = _candidate_route_progress(
                candidates[:, :route_horizon],
                route_centerline_ego,
            )
            reward_latency_breakdown_ms["latency_ms_reward_route_progress"] = (
                time.perf_counter() - reward_route_progress_start
            ) * 1000.0
        if min_candidate0_route_progress_ratio is not None:
            reward_route_progress_guard_start = time.perf_counter()
            (
                external_feasible_mask,
                external_infeasibility_reasons,
            ) = _apply_candidate0_route_progress_guard(
                external_feasible_mask,
                external_infeasibility_reasons,
                candidate_route_progress,
                min_candidate0_route_progress_ratio,
            )
            reward_latency_breakdown_ms["latency_ms_reward_route_progress_guard"] = (
                time.perf_counter() - reward_route_progress_guard_start
            ) * 1000.0
        if non_turn_logit_interaction_payload_logging:
            non_turn_logit_interaction_payload_logging_payload = (
                build_non_turn_logit_interaction_payload(
                    candidate_route_progress=candidate_route_progress,
                    candidate_dp_prior_jerk_excess_cost=(
                        candidate_dp_prior_jerk_excess_cost
                    ),
                    candidate_count=int(candidates.shape[0]),
                )
            )
            non_turn_logit_interaction_payload_latency_ms = (
                non_turn_logit_interaction_payload_logging_payload["latency_ms"]
            )
        if external_context_payload_logging:
            signal_context = build_current_tick_signal_context(
                red_route_points_ego=red_route_points,
                route_centerline_ego=route_centerline_ego,
                traffic_lights_enabled=bool(spawn_config.enable_traffic_lights),
            )
            external_context_payload_logging_payload = build_external_context_payload(
                candidates=candidates,
                route_centerline_ego=route_centerline_ego,
                support_steps=external_context_payload_steps,
                dt_s=external_context_payload_dt_s,
                signal_context=signal_context,
                route_speed_limit_mps=context.speed_limit,
                route_has_speed_limit=context.speed_limit is not None,
            )
            external_context_payload_latency_ms = (
                external_context_payload_logging_payload["latency_ms"]
            )
        if temporal_consistency_payload_logging:
            temporal_consistency_payload_logging_payload = (
                build_temporal_consistency_payload(
                    candidates=candidates,
                    previous_selected_plan=previous_selected_plan_memory,
                    support_steps=temporal_consistency_payload_steps,
                    dt_s=temporal_consistency_payload_dt_s,
                    elapsed_steps=temporal_consistency_payload_elapsed_steps,
                    min_overlap_steps=(
                        temporal_consistency_payload_min_overlap_steps
                    ),
                )
            )
            temporal_consistency_payload_latency_ms = (
                temporal_consistency_payload_logging_payload["latency_ms"]
            )
        if lexicographic_progress_epsilon_m is not None:
            if candidate_progress is None or candidate_planned_red_light_cost is None:
                raise RuntimeError(
                    "Lexicographic preselection requires DP reward candidate fields."
                )
            reward_lexicographic_filter_start = time.perf_counter()
            (
                external_feasible_mask,
                external_infeasibility_reasons,
                lexicographic_stage_counts,
            ) = _apply_lexicographic_admissible_filter(
                external_feasible_mask,
                external_infeasibility_reasons,
                candidate_progress=candidate_progress,
                candidate_planned_red_light_cost=(
                    candidate_planned_red_light_cost
                ),
                candidate_dp_prior_jerk_excess_cost=(
                    candidate_dp_prior_jerk_excess_cost
                ),
                candidate_horizon_lateral_acceleration_cost=(
                    candidate_horizon_lateral_acceleration_cost
                ),
                progress_epsilon_m=lexicographic_progress_epsilon_m,
                red_epsilon=lexicographic_red_epsilon,
                jerk_epsilon=lexicographic_jerk_epsilon,
                lateral_epsilon=lexicographic_lateral_epsilon,
            )
            reward_latency_breakdown_ms[
                "latency_ms_reward_lexicographic_filter"
            ] = (time.perf_counter() - reward_lexicographic_filter_start) * 1000.0
        reward_scoring_done = time.perf_counter()
        if collect_closed_loop_outcomes:
            candidate_outcomes = compute_candidate_closed_loop_outcomes(
                candidates,
                context,
                candidate_obstacles=obstacles,
                red_route_points=red_route_points,
                horizon_steps=outcome_horizon_steps,
                near_miss_threshold_m=near_miss_threshold_m,
                ego_length=ego_length,
                ego_width=ego_width,
                ego_wheelbase=ego_wheelbase,
                weights=outcome_weights,
            )
        outcome_collection_done = time.perf_counter()
        red_stopping_margin_start = time.perf_counter()
        candidate_red_stopping_margin_cost = compute_red_stopping_margin_costs(
            candidates,
            red_route_points,
            context.dt,
        )
        red_stopping_margin_done = time.perf_counter()
        shadow_red_stopping_margin_latency_ms = (
            red_stopping_margin_done - red_stopping_margin_start
        ) * 1000.0
        selection = selector.select(
            candidates,
            context,
            scene_embedding=scene_features if selector.mode == "linear" else None,
            candidate_obstacles=obstacles,
            candidate_progress=candidate_progress,
            candidate_planned_red_light_cost=candidate_planned_red_light_cost,
            candidate_red_stopping_margin_cost=candidate_red_stopping_margin_cost,
            candidate_dp_prior_jerk_excess_cost=(
                candidate_dp_prior_jerk_excess_cost
            ),
            external_feasible_mask=external_feasible_mask,
            external_infeasibility_reasons=external_infeasibility_reasons,
            apply_context_feasibility=feasibility_source == "context",
            ego_length=ego_length,
            ego_width=ego_width,
            ego_wheelbase=ego_wheelbase,
        )
        camp_selection_done = time.perf_counter()
        underprogress_relaxation_stats = None
        if underprogress_relaxation:
            if (
                candidate_progress is None
                or candidate_horizon_union_planned_red_light_cost is None
            ):
                raise RuntimeError(
                    "Underprogress relaxation requires DP reward candidate fields."
                )
            (
                selection,
                underprogress_relaxation_stats,
            ) = _apply_underprogress_relaxation_override(
                selection,
                candidates,
                candidate_progress=candidate_progress,
                candidate_union_red_cost=(
                    candidate_horizon_union_planned_red_light_cost
                ),
                candidate_red_stopping_margin_cost=(
                    candidate_red_stopping_margin_cost
                ),
                perfect_tracker_open_loop=perfect_tracker_open_loop,
                progress_loss_budget_m=underprogress_progress_loss_budget_m,
                h3_distance_loss_budget_m=(
                    underprogress_h3_distance_loss_budget_m
                ),
                lateral_limit_mps2=underprogress_lateral_limit_mps2,
            )
        underprogress_relaxation_done = time.perf_counter()
        baseline_selected_index = int(selection.selected_index)
        selected_index = baseline_selected_index
        splice_shadow_rule_stats = None
        if splice_shadow_rule:
            if (
                candidate_rewards is None
                or candidate_horizon_union_planned_red_light_cost is None
            ):
                raise RuntimeError(
                    "CAMP splice shadow rule requires DP reward candidate fields."
                )
            splice_shadow_rule_stats = _evaluate_splice_shadow_rule(
                replay_module=replay_module,
                tensor_converter_module=tensor_converter_module,
                scene=scene,
                map_cache=map_cache,
                model_args=model_args,
                candidates=candidates,
                baseline_selected_index=baseline_selected_index,
                candidate_rewards=candidate_rewards,
                candidate_union_red_cost=(
                    candidate_horizon_union_planned_red_light_cost
                ),
                device=device,
                reward_config=reward_config,
                spawn_config=spawn_config,
                reward_horizon_steps=reward_horizon_steps,
                anchor_steps=splice_shadow_anchor_steps,
                blend_steps=splice_shadow_blend_steps,
                heading_mode=splice_shadow_heading_mode,
                progress_loss_budget_m=(
                    splice_shadow_progress_loss_budget_m
                ),
                smoothness_loss_budget=(
                    splice_shadow_smoothness_loss_budget
                ),
            )
        splice_shadow_done = time.perf_counter()
        traffic_light_hybrid_postselection_stats = None
        if traffic_light_hybrid_postselection_mode != "off":
            if (
                candidate_progress is None
                or candidate_horizon_union_planned_red_light_cost is None
            ):
                raise RuntimeError(
                    "Traffic-light hybrid postselection requires DP reward "
                    "candidate fields."
                )
            (
                selected_index,
                traffic_light_hybrid_postselection_stats,
            ) = _apply_traffic_light_hybrid_postselection(
                selection,
                traffic_lights_enabled=bool(spawn_config.enable_traffic_lights),
                mode=traffic_light_hybrid_postselection_mode,
                candidate_step_reach=candidate_step_reach,
                candidate_progress=candidate_progress,
                candidate_union_red_cost=(
                    candidate_horizon_union_planned_red_light_cost
                ),
                candidate_red_stopping_margin_cost=(
                    candidate_red_stopping_margin_cost
                ),
                candidate_dp_prior_jerk_excess_cost=(
                    candidate_dp_prior_jerk_excess_cost
                ),
                candidate_horizon_lateral_acceleration_cost=(
                    candidate_horizon_lateral_acceleration_cost
                ),
                candidate_target_speed_mps=(
                    perfect_tracker_command["target_speed_mps"]
                ),
                perfect_tracker_open_loop=perfect_tracker_open_loop,
                red_route_point_count=int(red_route_points.shape[0]),
            )
        traffic_light_hybrid_done = time.perf_counter()
        perfect_tracker_command_postselection_stats = None
        if perfect_tracker_command_postselection:
            if candidate_progress is None or candidate_planned_red_light_cost is None:
                raise RuntimeError(
                    "PerfectTracker command postselection requires DP reward "
                    "candidate fields."
                )
            (
                selected_index,
                perfect_tracker_command_postselection_stats,
            ) = select_perfect_tracker_command_dominating_candidate(
                baseline_selected_index=baseline_selected_index,
                feasible_mask=selection.feasible_mask,
                selection_scores=selection.selection_scores,
                candidate_progress=candidate_progress,
                candidate_planned_red_light_cost=(
                    candidate_planned_red_light_cost
                ),
                candidate_target_speed_mps=perfect_tracker_command[
                    "target_speed_mps"
                ],
                candidate_jerk_magnitude_mps3=perfect_tracker_command[
                    "jerk_magnitude_mps3"
                ],
                candidate_lateral_acceleration_magnitude_mps2=(
                    perfect_tracker_command[
                        "lateral_acceleration_magnitude_mps2"
                    ]
                ),
            )
        selection_done = time.perf_counter()
        elapsed_ms = (selection_done - start) * 1000.0
        phase_latencies_ms = {
            "latency_ms_candidate_generation": (
                candidate_generation_done - start
            )
            * 1000.0,
            "latency_ms_shadow_dp_prior_deviation": (
                shadow_dp_prior_deviation_latency_ms
            ),
            **observable_state_latency_ms,
            **progress_support_latency_ms,
            **lane_hard_violation_support_latency_ms,
            **progress_lane_hard_context_latency_ms,
            **turn_logit_payload_latency_ms,
            **non_turn_logit_interaction_payload_latency_ms,
            **external_context_payload_latency_ms,
            **temporal_consistency_payload_latency_ms,
            "latency_ms_context_and_obstacles": (
                context_and_obstacles_done - lateral_comfort_done
            )
            * 1000.0,
            "latency_ms_reward_scoring": (
                reward_scoring_done - perfect_tracker_open_loop_done
            )
            * 1000.0,
            **reward_latency_breakdown_ms,
            "latency_ms_shadow_perfect_tracker_command": (
                shadow_perfect_tracker_command_latency_ms
            ),
            "latency_ms_shadow_perfect_tracker_open_loop": (
                shadow_perfect_tracker_open_loop_latency_ms
            ),
            "latency_ms_shadow_full_horizon_red_light": (
                full_horizon_red_light_latency_ms
            ),
            "latency_ms_outcome_collection": (
                outcome_collection_done - reward_scoring_done
            )
            * 1000.0,
            "latency_ms_red_stopping_margin_atom": (
                red_stopping_margin_done - outcome_collection_done
            )
            * 1000.0,
            "latency_ms_camp_selection": (
                camp_selection_done - red_stopping_margin_done
            )
            * 1000.0,
            "latency_ms_underprogress_relaxation": (
                underprogress_relaxation_done - camp_selection_done
            )
            * 1000.0,
            "latency_ms_perfect_tracker_command_postselection": (
                selection_done - traffic_light_hybrid_done
            )
            * 1000.0,
            "latency_ms_traffic_light_hybrid_postselection": (
                traffic_light_hybrid_done - splice_shadow_done
            )
            * 1000.0,
            "latency_ms_splice_shadow_rule": (
                splice_shadow_done - underprogress_relaxation_done
            )
            * 1000.0,
            "latency_ms_red_route_vector_logging": red_route_vector_latency_ms,
            "latency_ms_camp_atom_computation": selection.timings_ms[
                "atom_computation"
            ],
            "latency_ms_camp_feasibility": selection.timings_ms["feasibility"],
            "latency_ms_camp_collision_checks": selection.timings_ms[
                "collision_checks"
            ],
            "latency_ms_camp_scoring": selection.timings_ms["scoring"],
        }

        selection_step = len(records)
        if (
            microbenchmark_snapshot_dir is not None
            and selection_step in microbenchmark_snapshot_steps
        ):
            _write_microbenchmark_snapshot(
                output_dir=microbenchmark_snapshot_dir,
                selection_step=selection_step,
                normalized_inputs=inputs,
                tensor_converter_module=tensor_converter_module,
                scene=scene,
                map_cache=map_cache,
                model_args=model_args,
                candidates=candidates,
                neighbor_predictions=neighbor_predictions,
                candidate_obstacles=obstacles,
                context=context,
                selector=selector,
                selection=selection,
                scene_features=scene_features,
                external_feasible_mask=external_feasible_mask,
                external_infeasibility_reasons=external_infeasibility_reasons,
                candidate_progress=candidate_progress,
                candidate_planned_red_light_cost=candidate_planned_red_light_cost,
                candidate_full_horizon_planned_red_light_cost=(
                    candidate_full_horizon_planned_red_light_cost
                ),
                candidate_red_stopping_margin_cost=(
                    candidate_red_stopping_margin_cost
                ),
                candidate_dp_prior_jerk_excess_cost=(
                    candidate_dp_prior_jerk_excess_cost
                ),
                candidate_generation_contract=candidate_generation_contract,
                red_route_points=red_route_points,
                perfect_tracker_current_speed_mps=(
                    perfect_tracker_current_speed_mps
                ),
                perfect_tracker_current_longitudinal_acceleration_mps2=(
                    perfect_tracker_current_longitudinal_acceleration_mps2
                ),
                perfect_tracker_current_acceleration_ego_xy=(
                    perfect_tracker_current_acceleration_ego_xy
                ),
                num_candidates=num_candidates,
                noise_scale=noise_scale,
                reference_blend_steps=reference_blend_steps,
                reward_horizon_steps=reward_horizon_steps,
                outcome_horizon_steps=outcome_horizon_steps,
                spawn_config=spawn_config,
            )

        selected_trajectory = candidates[selected_index]
        predictions[ego_id] = selected_trajectory
        previous_selected_plan_memory = np.asarray(
            selected_trajectory,
            dtype=np.float64,
        ).copy()
        state = _evaluation_state(scene, ego_id)
        state["step"] = len(evaluation_records)
        evaluation_records.append(state)
        _append_metric_record(
            replay_module=replay_module,
            tensor_converter_module=tensor_converter_module,
            scene=scene,
            map_cache=map_cache,
            model_args=model_args,
            prediction=selected_trajectory,
            device=device,
            reward_config=reward_config,
            spawn_config=spawn_config,
            records=metric_records,
        )
        if return_turn_indicators and turn_logits is not None:
            chosen_logits = turn_logits[selected_index].copy()
            if turn_indicator_keep_bias != 0.0 and chosen_logits.shape[-1] > 4:
                chosen_logits[4] -= turn_indicator_keep_bias
            turn_indicators[ego_id] = int(np.argmax(chosen_logits))

        raw_candidate_prefix_payload = _raw_candidate_prefix_payload(
            candidates,
            raw_candidate_prefix_steps,
        )
        records.append(
            {
                "selection_step": len(records),
                "selected_index": selected_index,
                "camp_selected_index_before_tracker_postselection": (
                    baseline_selected_index
                    if perfect_tracker_command_postselection
                    else None
                ),
                "camp_selected_index_before_traffic_light_hybrid_postselection": (
                    baseline_selected_index
                    if traffic_light_hybrid_postselection_mode != "off"
                    else None
                ),
                "perfect_tracker_command_postselection": (
                    perfect_tracker_command_postselection_stats
                ),
                "traffic_light_hybrid_postselection": (
                    traffic_light_hybrid_postselection_stats
                ),
                "underprogress_relaxation": underprogress_relaxation_stats,
                "splice_shadow_rule": splice_shadow_rule_stats,
                "num_candidates": int(num_candidates),
                "candidate_noise_scale": float(noise_scale),
                "candidate_reference_blend_steps": reference_blend_steps,
                "candidate_generation_contract": candidate_generation_contract,
                "candidate_trajectory_horizon_steps": int(candidates.shape[1]),
                "candidate_first_reference_xy": (
                    candidates[:, 0, :2].tolist()
                ),
                **raw_candidate_prefix_payload,
                "candidate_perfect_tracker_reference_first_xy": (
                    perfect_tracker_command[
                        "first_reference_xy"
                    ].tolist()
                ),
                "candidate_perfect_tracker_reference_first_heading_rad": (
                    perfect_tracker_command[
                        "first_reference_heading_rad"
                    ].tolist()
                ),
                "candidate_perfect_tracker_first_step_reach_m": (
                    perfect_tracker_command["first_step_reach_m"].tolist()
                ),
                "candidate_perfect_tracker_postprocessed_tail_xy": (
                    perfect_tracker_command[
                        "postprocessed_tail_reference_xy"
                    ].tolist()
                ),
                "candidate_perfect_tracker_postprocessed_reference_prefix": (
                    perfect_tracker_command["postprocessed_reference"][
                        :, : PERFECT_TRACKER_OPEN_LOOP_HORIZONS[-1]
                    ].tolist()
                ),
                "perfect_tracker_command_inputs": {
                    "dt": float(getattr(scene, "dt", 0.1)),
                    "current_speed_mps": perfect_tracker_current_speed_mps,
                    "current_longitudinal_acceleration_mps2": (
                        perfect_tracker_current_longitudinal_acceleration_mps2
                    ),
                    "max_speed_mps": 20.0,
                    "velocity_smooth_window": 8,
                    "stop_threshold_mps": 0.3,
                    "restart_speed_threshold_mps": 0.1,
                    "restart_plan_speed_threshold_mps": 0.5,
                },
                "perfect_tracker_open_loop_rollout_inputs": {
                    "full_horizon_steps": int(candidates.shape[1]),
                    "horizons": list(PERFECT_TRACKER_OPEN_LOOP_HORIZONS),
                    "dt": float(getattr(scene, "dt", 0.1)),
                    "current_speed_mps": perfect_tracker_current_speed_mps,
                    "current_acceleration_ego_xy": (
                        perfect_tracker_current_acceleration_ego_xy.tolist()
                    ),
                    "max_speed_mps": 20.0,
                    "restart_speed_threshold_mps": 0.1,
                    "restart_plan_speed_threshold_mps": 0.5,
                },
                "candidate_perfect_tracker_open_loop_rollout": {
                    horizon: {
                        metric: values.tolist()
                        for metric, values in metrics.items()
                    }
                    for horizon, metrics in perfect_tracker_open_loop[
                        "horizons"
                    ].items()
                },
                "perfect_tracker_candidate_preprocessing": (
                    _perfect_tracker_candidate_preprocessing(spawn_config)
                ),
                "candidate_perfect_tracker_tail_average_speed_mps": (
                    perfect_tracker_command["tail_average_speed_mps"].tolist()
                ),
                "candidate_perfect_tracker_restart_push": (
                    perfect_tracker_command["restart_push"].tolist()
                ),
                "candidate_perfect_tracker_target_speed_mps": (
                    perfect_tracker_command["target_speed_mps"].tolist()
                ),
                "candidate_perfect_tracker_acceleration_mps2": (
                    perfect_tracker_command["acceleration_mps2"].tolist()
                ),
                "candidate_perfect_tracker_jerk_magnitude_mps3": (
                    perfect_tracker_command[
                        "jerk_magnitude_mps3"
                    ].tolist()
                ),
                "candidate_perfect_tracker_yaw_rate_magnitude_rps": (
                    perfect_tracker_command[
                        "yaw_rate_magnitude_rps"
                    ].tolist()
                ),
                "candidate_perfect_tracker_lateral_acceleration_magnitude_mps2": (
                    perfect_tracker_command[
                        "lateral_acceleration_magnitude_mps2"
                    ].tolist()
                ),
                "used_fallback": selection.used_fallback,
                "camp_fallback_mode": getattr(selector, "fallback_mode", "uniform")
                if selector is not None
                else None,
                "feasible_mask": selection.feasible_mask.tolist(),
                "infeasibility_reasons": [
                    list(reasons) for reasons in selection.infeasibility_reasons
                ],
                "scores": selection.scores.tolist(),
                "weights": selection.weights.tolist(),
                "selection_scores": selection.selection_scores.tolist(),
                "selection_weights": selection.selection_weights.tolist(),
                "atoms": selection.atoms.tolist(),
                "normalized_atoms": selection.normalized_atoms.tolist(),
                "selection_normalized_atoms": (
                    selection.selection_normalized_atoms.tolist()
                ),
                "atom_schema_version": atom_schema_for_dimension(
                    selection.atoms.shape[1]
                )[0],
                "atom_names": list(
                    atom_schema_for_dimension(selection.atoms.shape[1])[1]
                ),
                "dp_candidate_rewards": candidate_rewards,
                "dp_candidate_reward_horizon_steps": (
                    min(reward_horizon_steps, int(candidates.shape[1]))
                    if candidate_rewards is not None
                    else None
                ),
                "candidate_full_horizon_planned_red_light_cost": (
                    candidate_full_horizon_planned_red_light_cost.tolist()
                    if candidate_full_horizon_planned_red_light_cost is not None
                    else None
                ),
                "candidate_full_horizon_red_light_horizon_steps": (
                    int(candidates.shape[1])
                    if candidate_full_horizon_planned_red_light_cost is not None
                    else None
                ),
                "candidate_horizon_union_planned_red_light_cost": (
                    candidate_horizon_union_planned_red_light_cost.tolist()
                    if candidate_horizon_union_planned_red_light_cost is not None
                    else None
                ),
                "candidate_route_progress": (
                    candidate_route_progress.tolist()
                    if candidate_route_progress is not None
                    else None
                ),
                "observable_state_logging": observable_state_logging_payload,
                "red_route_vector_logging": red_route_vector_logging_payload,
                "progress_support_logging": progress_support_logging_payload,
                "lane_hard_violation_support_logging": (
                    lane_hard_violation_support_logging_payload
                ),
                "progress_lane_hard_context_logging": (
                    progress_lane_hard_context_logging_payload
                ),
                "turn_logit_payload_logging": turn_logit_payload_logging_payload,
                "non_turn_logit_interaction_payload_logging": (
                    non_turn_logit_interaction_payload_logging_payload
                ),
                "external_context_payload_logging": (
                    external_context_payload_logging_payload
                ),
                "temporal_consistency_payload_logging": (
                    temporal_consistency_payload_logging_payload
                ),
                "candidate_obstacle_clearance": candidate_obstacle_clearance,
                "candidate_step_reach": (
                    candidate_step_reach.tolist()
                    if candidate_step_reach is not None
                    else None
                ),
                "candidate_step_reach_guard_relaxed": (
                    bool(candidate_step_reach_guard_relaxed)
                    if min_candidate0_step_reach_ratio is not None
                    else None
                ),
                "lexicographic_stage_counts": lexicographic_stage_counts,
                "candidate_closed_loop_outcomes": candidate_outcomes,
                "candidate_red_stopping_margin_cost": (
                    candidate_red_stopping_margin_cost.tolist()
                ),
                "candidate_dp_prior_deviation_cost": (
                    candidate_dp_prior_deviation_cost.tolist()
                ),
                "candidate_dp_prior_jerk_excess_cost": (
                    candidate_dp_prior_jerk_excess_cost.tolist()
                ),
                "candidate_dp_prior_acceleration_excess_cost": (
                    candidate_dp_prior_acceleration_excess_cost.tolist()
                ),
                "candidate_dp_prior_comfort_excess_horizon_steps": (
                    dp_prior_comfort_horizon_steps
                ),
                "candidate_horizon_lateral_acceleration_cost": (
                    candidate_horizon_lateral_acceleration_cost.tolist()
                ),
                "candidate_dp_prior_lateral_acceleration_excess_cost": (
                    candidate_dp_prior_lateral_acceleration_excess_cost.tolist()
                ),
                "candidate_horizon_yaw_rate_cost": (
                    candidate_horizon_yaw_rate_cost.tolist()
                ),
                "candidate_dp_prior_yaw_rate_excess_cost": (
                    candidate_dp_prior_yaw_rate_excess_cost.tolist()
                ),
                "candidate_lateral_comfort_horizon_steps": (
                    lateral_comfort_horizon_steps
                ),
                "red_route_point_count": int(red_route_points.shape[0]),
                "latency_ms_shadow_red_stopping_margin": (
                    shadow_red_stopping_margin_latency_ms
                ),
                "latency_ms_shadow_dp_prior_comfort_excess": (
                    shadow_dp_prior_comfort_excess_latency_ms
                ),
                "latency_ms_shadow_lateral_comfort": (
                    shadow_lateral_comfort_latency_ms
                ),
                "latency_ms_shadow_obstacle_clearance": (
                    shadow_obstacle_clearance_latency_ms
                ),
                "red_stopping_margin_used_as_atom": (
                    "red_stopping_margin_cost"
                    in atom_schema_for_dimension(selection.atoms.shape[1])[1]
                ),
                "dp_prior_jerk_excess_used_as_atom": (
                    "dp_prior_jerk_excess_cost"
                    in atom_schema_for_dimension(selection.atoms.shape[1])[1]
                ),
                "candidate_closed_loop_outcome_horizon_steps": (
                    min(outcome_horizon_steps, int(candidates.shape[1]))
                    if candidate_outcomes is not None
                    else None
                ),
                "candidate_closed_loop_outcome_weights": (
                    outcome_weights if candidate_outcomes is not None else None
                ),
                "dp_scene_features": scene_features.tolist(),
                "dp_scene_feature_names": list(DP_SCENE_FEATURE_NAMES),
                "latency_ms_including_candidate_generation": elapsed_ms,
                **phase_latencies_ms,
            }
        )
        if return_turn_indicators:
            return predictions, turn_indicators
        return predictions

    replay_module._predict_batch = camp_predict
    return original_predict, records, metric_records, evaluation_records


def main() -> None:
    args = parse_args()
    _validate_args(args)

    _install_diffusion_repo(args.diffusion_repo)

    import torch
    import scenario_generation.replay as replay
    import scenario_generation.tensor_converter as tensor_converter
    from scenario_generation.gui.lanelet_scene_builder import LaneletSceneBuilder
    from scenario_generation.route import Route
    from rlvr.autoresearch.tools.reward_config_from_json import load_reward_config

    route = Route.load(args.route)
    map_path = args.map_path or route.map_path
    using_projection_fallback = install_lanelet2_projection_fallback(map_path)
    builder = LaneletSceneBuilder(map_path)
    config = replay.SpawnConfig.from_json(args.config)
    if args.steps is not None:
        config.max_steps = args.steps
    if args.seed is not None:
        config.seed = args.seed
    if args.max_npcs is not None:
        config.max_active_npcs = args.max_npcs
    if args.spawn_probability is not None:
        config.spawn_probability = args.spawn_probability
    if args.advance_mode != "config":
        config.advance_mode = args.advance_mode
    if args.traffic_lights != "config":
        config.enable_traffic_lights = args.traffic_lights == "on"
    config.validate()
    if (
        args.camp_perfect_tracker_command_postselection
        and config.advance_mode != "perfect"
    ):
        raise ValueError(
            "PerfectTracker command postselection requires "
            "advance_mode='perfect'."
        )

    device = args.device if torch.cuda.is_available() or args.device == "cpu" else "cpu"
    model, model_args = _load_model(args.model_path, args.model_args, device)
    candidate_guidance = _configure_candidate_guidance(
        model,
        guidance_config_path=args.candidate_guidance_config,
        guidance_scale=args.candidate_guidance_scale,
    )
    candidate_generation_contract = _candidate_generation_contract(
        model_args,
        num_candidates=args.num_candidates,
        noise_scale=args.candidate_noise_scale,
        noise_strategy=args.candidate_noise_strategy,
        reference_blend_steps=args.candidate_reference_blend_steps,
        guidance=candidate_guidance,
    )
    reward_config = (
        load_reward_config(args.reward_config)
        if args.reward_config is not None
        else None
    )
    selector = _build_selector(args)
    records: list[dict[str, Any]] | None = None
    metric_records: list[dict[str, Any]] = []
    evaluation_records: list[dict[str, Any]] = []
    original_predict = None
    if selector is not None:
        route_centerline = _route_centerline_world(builder, route)
        (
            original_predict,
            records,
            metric_records,
            evaluation_records,
        ) = _install_camp_predictor(
            replay,
            tensor_converter,
            selector,
            num_candidates=args.num_candidates,
            noise_scale=args.candidate_noise_scale,
            reference_blend_steps=args.candidate_reference_blend_steps,
            candidate_generation_contract=candidate_generation_contract,
            safety_radius=args.camp_safety_radius,
            clearance_margin=args.camp_clearance_margin,
            lane_corridor_buffer=args.camp_lane_corridor_buffer,
            feasibility_source=args.camp_feasibility_source,
            min_progress_ratio=args.camp_min_progress_ratio,
            min_candidate0_progress_ratio=args.camp_min_candidate0_progress_ratio,
            min_candidate0_route_progress_ratio=(
                args.camp_min_candidate0_route_progress_ratio
            ),
            shadow_route_progress=bool(args.camp_shadow_route_progress),
            shadow_obstacle_clearance=bool(args.camp_shadow_obstacle_clearance),
            shadow_obstacle_clearance_exact_obb=bool(
                args.camp_shadow_obstacle_clearance_exact_obb
            ),
            min_candidate0_step_reach_ratio=(
                args.camp_min_candidate0_step_reach_ratio
            ),
            candidate0_step_reach_preserve_feasible=(
                bool(args.camp_candidate0_step_reach_preserve_feasible)
            ),
            lexicographic_progress_epsilon_m=(
                args.camp_lexicographic_progress_epsilon_m
            ),
            lexicographic_red_epsilon=args.camp_lexicographic_red_epsilon,
            lexicographic_jerk_epsilon=args.camp_lexicographic_jerk_epsilon,
            lexicographic_lateral_epsilon=(
                args.camp_lexicographic_lateral_epsilon
            ),
            perfect_tracker_command_postselection=(
                bool(args.camp_perfect_tracker_command_postselection)
            ),
            traffic_light_hybrid_postselection_mode=(
                args.camp_traffic_light_hybrid_postselection
            ),
            underprogress_relaxation=bool(args.camp_underprogress_relaxation),
            underprogress_progress_loss_budget_m=(
                args.camp_underprogress_progress_loss_budget_m
            ),
            underprogress_h3_distance_loss_budget_m=(
                args.camp_underprogress_h3_distance_loss_budget_m
            ),
            underprogress_lateral_limit_mps2=(
                args.camp_underprogress_lateral_limit_mps2
            ),
            reward_horizon_steps=args.camp_reward_horizon_steps,
            collect_closed_loop_outcomes=args.camp_collect_closed_loop_outcomes,
            outcome_horizon_steps=args.camp_outcome_horizon_steps,
            outcome_weights={
                "progress": args.camp_outcome_progress_weight,
                "collision": args.camp_outcome_collision_penalty,
                "near_miss": args.camp_outcome_near_miss_penalty,
                "lane_violation": args.camp_outcome_lane_penalty,
                "red_light": args.camp_outcome_red_light_penalty,
                "mean_jerk": args.camp_outcome_jerk_penalty,
                "mean_lateral_acceleration": (
                    args.camp_outcome_lateral_acceleration_penalty
                ),
            },
            near_miss_threshold_m=args.near_miss_threshold_m,
            ego_length=float(config.ego_length),
            ego_width=float(config.ego_width),
            ego_wheelbase=float(config.ego_wheelbase),
            reward_config=reward_config,
            spawn_config=config,
            route_centerline=route_centerline,
            observable_state_logging=bool(args.camp_observable_state_logging),
            observable_state_support_steps=(
                args.camp_observable_state_support_steps
            ),
            observable_state_traffic_light_steps=(
                args.camp_observable_state_traffic_light_steps
            ),
            observable_state_turn_steps=args.camp_observable_state_turn_steps,
            red_route_vector_logging=bool(args.camp_red_route_vector_logging),
            progress_support_logging=bool(args.camp_progress_support_logging),
            progress_support_steps=args.camp_progress_support_steps,
            progress_support_dt_s=args.camp_progress_support_dt_s,
            lane_hard_violation_support_logging=bool(
                args.camp_lane_hard_violation_support_logging
            ),
            lane_hard_violation_support_steps=(
                args.camp_lane_hard_violation_support_steps
            ),
            lane_hard_violation_support_dt_s=(
                args.camp_lane_hard_violation_support_dt_s
            ),
            lane_hard_violation_corridor_half_width_m=(
                args.camp_lane_hard_violation_corridor_half_width_m
            ),
            lane_hard_violation_lateral_rate_budget_mps=(
                args.camp_lane_hard_violation_lateral_rate_budget_mps
            ),
            progress_lane_hard_context_logging=bool(
                args.camp_progress_lane_hard_context_logging
            ),
            progress_lane_hard_context_steps=(
                args.camp_progress_lane_hard_context_steps
            ),
            progress_lane_hard_context_dt_s=(
                args.camp_progress_lane_hard_context_dt_s
            ),
            progress_lane_hard_context_corridor_half_width_m=(
                args.camp_progress_lane_hard_context_corridor_half_width_m
            ),
            progress_lane_hard_context_corridor_safety_margin_m=(
                args.camp_progress_lane_hard_context_corridor_safety_margin_m
            ),
            turn_logit_payload_logging=bool(args.camp_turn_logit_payload_logging),
            non_turn_logit_interaction_payload_logging=bool(
                args.camp_non_turn_logit_interaction_payload_logging
            ),
            external_context_payload_logging=bool(
                args.camp_external_context_payload_logging
            ),
            external_context_payload_steps=args.camp_external_context_payload_steps,
            external_context_payload_dt_s=args.camp_external_context_payload_dt_s,
            temporal_consistency_payload_logging=bool(
                args.camp_temporal_consistency_payload_logging
            ),
            temporal_consistency_payload_steps=(
                args.camp_temporal_consistency_payload_steps
            ),
            temporal_consistency_payload_dt_s=(
                args.camp_temporal_consistency_payload_dt_s
            ),
            temporal_consistency_payload_elapsed_steps=(
                args.camp_temporal_consistency_payload_elapsed_steps
            ),
            temporal_consistency_payload_min_overlap_steps=(
                args.camp_temporal_consistency_payload_min_overlap_steps
            ),
            microbenchmark_snapshot_dir=(
                args.camp_microbenchmark_snapshot_dir
            ),
            microbenchmark_snapshot_steps=(
                args.camp_microbenchmark_snapshot_steps
            ),
            raw_candidate_prefix_steps=args.camp_log_raw_candidate_prefix_steps,
            splice_shadow_rule=bool(args.camp_splice_shadow_rule),
            splice_shadow_anchor_steps=args.camp_splice_shadow_anchor_steps,
            splice_shadow_blend_steps=args.camp_splice_shadow_blend_steps,
            splice_shadow_heading_mode=args.camp_splice_shadow_heading_mode,
            splice_shadow_progress_loss_budget_m=(
                args.camp_splice_shadow_progress_loss_budget_m
            ),
            splice_shadow_smoothness_loss_budget=(
                args.camp_splice_shadow_smoothness_loss_budget
            ),
        )
    else:
        (
            original_predict,
            metric_records,
            evaluation_records,
        ) = _install_top1_observer(
            replay,
            tensor_converter,
            reward_config=reward_config,
            spawn_config=config,
        )

    try:
        result = replay.run_route_replay(
            model=model,
            model_args=model_args,
            builder=builder,
            route=route,
            output_dir=args.output_dir,
            spawn_config=config,
            device=device,
        )
    finally:
        if original_predict is not None:
            replay._predict_batch = original_predict

    args.output_dir.mkdir(parents=True, exist_ok=True)
    selection_log = None
    if records is not None:
        selection_log = args.output_dir / "camp_selection_log.json"
        selection_log.write_text(json.dumps(records, indent=2), encoding="utf-8")
    metric_log = args.output_dir / "camp_metric_log.json"
    metric_log.write_text(json.dumps(metric_records, indent=2), encoding="utf-8")
    evaluation_log = args.output_dir / "camp_evaluation_state_log.json"
    evaluation_log.write_text(
        json.dumps(evaluation_records, indent=2),
        encoding="utf-8",
    )
    effective_num_candidates = args.num_candidates if records is not None else 1
    effective_noise_scale = args.candidate_noise_scale if records is not None else None
    effective_reference_blend = (
        {
            "enabled": True,
            "steps": int(args.candidate_reference_blend_steps),
            "reference_candidate_index": 0,
            "weight_definition": "min(t / steps, 1)",
            "first_reference_xy_preserved": True,
            "selection_effect": True,
        }
        if records is not None
        and args.candidate_reference_blend_steps is not None
        else None
    )
    effective_lane_buffer = (
        args.camp_lane_corridor_buffer if records is not None else None
    )
    effective_feasibility_source = (
        args.camp_feasibility_source if records is not None else None
    )
    effective_min_progress_ratio = (
        args.camp_min_progress_ratio
        if records is not None and args.camp_feasibility_source == "dp_reward"
        else None
    )
    effective_min_candidate0_progress_ratio = (
        args.camp_min_candidate0_progress_ratio
        if records is not None
        and args.camp_feasibility_source == "dp_reward"
        else None
    )
    effective_min_candidate0_route_progress_ratio = (
        args.camp_min_candidate0_route_progress_ratio
        if records is not None
        else None
    )
    effective_shadow_route_progress = (
        bool(args.camp_shadow_route_progress) if records is not None else None
    )
    effective_shadow_obstacle_clearance = (
        bool(args.camp_shadow_obstacle_clearance) if records is not None else None
    )
    effective_min_candidate0_step_reach_ratio = (
        args.camp_min_candidate0_step_reach_ratio
        if records is not None
        else None
    )
    effective_candidate0_step_reach_preserve_feasible = (
        bool(args.camp_candidate0_step_reach_preserve_feasible)
        if records is not None and args.camp_min_candidate0_step_reach_ratio is not None
        else None
    )
    effective_lexicographic_preselection = (
        {
            "enabled": True,
            "order": ["progress", "planned_red", "jerk", "lateral"],
            "progress_epsilon_m": float(
                args.camp_lexicographic_progress_epsilon_m
            ),
            "planned_red_epsilon": float(args.camp_lexicographic_red_epsilon),
            "jerk_epsilon": float(args.camp_lexicographic_jerk_epsilon),
            "lateral_epsilon": float(args.camp_lexicographic_lateral_epsilon),
            "selection_effect": True,
        }
        if records is not None
        and args.camp_lexicographic_progress_epsilon_m is not None
        else None
    )
    effective_perfect_tracker_command_postselection = (
        {
            "enabled": True,
            "selection_effect": True,
            "baseline": "camp_selected_index",
            "required_nonworse": [
                "base_feasibility",
                "perfect_tracker_target_speed",
                "dp_progress",
                "planned_red",
                "perfect_tracker_command_jerk",
                "perfect_tracker_command_lateral_acceleration",
            ],
            "required_strict_improvement": [
                "perfect_tracker_command_jerk",
                "perfect_tracker_command_lateral_acceleration",
            ],
            "order": [
                "perfect_tracker_command_jerk",
                "perfect_tracker_command_lateral_acceleration",
                "camp_score",
                "candidate_index",
            ],
            "epsilons": {
                "target_speed_mps": 0.0,
                "progress_m": 0.0,
                "planned_red": 0.0,
                "jerk_mps3": 0.0,
                "lateral_acceleration_mps2": 0.0,
            },
            "new_fallback_possible": False,
        }
        if records is not None
        and args.camp_perfect_tracker_command_postselection
        else None
    )
    effective_underprogress_relaxation = (
        {
            "enabled": True,
            "selection_effect": True,
            "ignored_reason": "dp_underprogress",
            "requires_stopping_margin_nonworse": True,
            "hard_reasons_remain_hard": True,
            "order": [
                "union_red",
                "red_stopping_margin",
                "camp_score",
                "candidate_index",
            ],
            "progress_loss_budget_m": float(
                args.camp_underprogress_progress_loss_budget_m
            ),
            "h3_distance_loss_budget_m": float(
                args.camp_underprogress_h3_distance_loss_budget_m
            ),
            "h3_max_lateral_limit_mps2": float(
                args.camp_underprogress_lateral_limit_mps2
            ),
        }
        if records is not None and args.camp_underprogress_relaxation
        else None
    )
    effective_reward_horizon_steps = (
        args.camp_reward_horizon_steps
        if records is not None and args.camp_feasibility_source == "dp_reward"
        else None
    )
    effective_comfort_shadow_horizon_steps = (
        records[0]["candidate_dp_prior_comfort_excess_horizon_steps"]
        if records
        else None
    )
    effective_lateral_comfort_horizon_steps = (
        records[0]["candidate_lateral_comfort_horizon_steps"]
        if records
        else None
    )
    microbenchmark_snapshot_paths = (
        sorted(args.camp_microbenchmark_snapshot_dir.glob("*.npz"))
        if args.camp_microbenchmark_snapshot_dir is not None
        else []
    )
    camp_raw_candidate_prefix_logging = (
        {
            "enabled": args.camp_log_raw_candidate_prefix_steps > 0,
            "selection_effect": False,
            "steps": int(args.camp_log_raw_candidate_prefix_steps),
            "field": "candidate_raw_trajectory_prefix",
            "dimensions": (
                "raw Diffusion Planner ego candidate state prefix "
                "[x, y, cos_yaw, sin_yaw]"
            ),
            "purpose": "offline raw-candidate geometry audits only",
        }
        if records is not None
        else None
    )
    camp_observable_state_logging = (
        {
            "schema_version": OBSERVABLE_STATE_LOGGING_SCHEMA_VERSION,
            "enabled": bool(args.camp_observable_state_logging),
            "default_off": True,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "online_selector_change": False,
            "authorized_stage": (
                "unit_tested_default_off_preflight_only"
            ),
            "logged_field": "observable_state_logging",
            "fields": list(OBSERVABLE_STATE_FIELDS),
            "latency_fields": list(OBSERVABLE_STATE_LATENCY_KEYS),
            "horizons": {
                "support_steps": int(args.camp_observable_state_support_steps),
                "traffic_light_steps": int(
                    args.camp_observable_state_traffic_light_steps
                ),
                "turn_steps": int(args.camp_observable_state_turn_steps),
            },
            "records": (
                int(
                    sum(
                        1
                        for record in records
                        if record.get("observable_state_logging") is not None
                    )
                )
                if args.camp_observable_state_logging
                else 0
            ),
            "latency_ms": (
                {
                    key: _summary(
                        [
                            float(record[key])
                            for record in records
                            if key in record and record[key] is not None
                        ]
                    )
                    for key in OBSERVABLE_STATE_LATENCY_KEYS
                }
                if args.camp_observable_state_logging
                else None
            ),
            "definition": (
                "current-tick fixed-candidate route topology, traffic-light "
                "relation, turn-context, and neighbor-clearance descriptors "
                "computed before closed-loop outcome labels"
            ),
            "math_boundary": (
                "If later atomized, each field is a fixed finite-candidate "
                "quantity; CAMP score remains affine in weights and the "
                "simplex/CVaR/L2 master remains convex."
            ),
            "classical_benders_claim": False,
        }
        if records is not None
        else None
    )
    camp_red_route_vector_logging = (
        {
            "schema_version": RED_ROUTE_VECTOR_LOGGING_SCHEMA_VERSION,
            "enabled": bool(args.camp_red_route_vector_logging),
            "default_off": True,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "closed_loop_outcome_fields_read": False,
            "online_selector_change": False,
            "authorized_stage": "unit_tests_only_default_off_preflight",
            "logged_field": "red_route_vector_logging",
            "fields": list(RED_ROUTE_VECTOR_FIELDS),
            "latency_fields": list(RED_ROUTE_VECTOR_LATENCY_KEYS),
            "horizons": {
                "traffic_light_steps": int(
                    args.camp_observable_state_traffic_light_steps
                ),
            },
            "records": (
                int(
                    sum(
                        1
                        for record in records
                        if record.get("red_route_vector_logging") is not None
                    )
                )
                if args.camp_red_route_vector_logging
                else 0
            ),
            "latency_ms": (
                {
                    key: _summary(
                        [
                            float(record[key])
                            for record in records
                            if key in record and record[key] is not None
                        ]
                    )
                    for key in RED_ROUTE_VECTOR_LATENCY_KEYS
                }
                if args.camp_red_route_vector_logging
                else None
            ),
            "definition": (
                "current-tick fixed-candidate red route point and candidate "
                "heading vector diagnostics computed before closed-loop outcomes"
            ),
            "math_boundary": (
                "These fields are diagnostics only. If a later red descriptor is "
                "atomized, it must be a fixed pre-outcome nonnegative candidate "
                "coefficient; CAMP score remains affine in weights and the "
                "simplex/CVaR/L2 master remains convex."
            ),
            "classical_benders_claim": False,
        }
        if records is not None
        else None
    )
    camp_progress_support_logging = (
        {
            "schema_version": PROGRESS_SUPPORT_LOGGING_SCHEMA_VERSION,
            "enabled": bool(args.camp_progress_support_logging),
            "default_off": True,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "closed_loop_outcome_fields_read": False,
            "online_selector_change": False,
            "authorized_stage": "unit_tests_only_default_off_preflight",
            "logged_field": "progress_support_logging",
            "fields": list(PROGRESS_SUPPORT_FIELD_NAMES),
            "atom_names": list(PROGRESS_SUPPORT_ATOM_NAMES),
            "latency_fields": list(PROGRESS_SUPPORT_LATENCY_KEYS),
            "horizons": {
                "support_steps": int(args.camp_progress_support_steps),
                "dt_s": float(args.camp_progress_support_dt_s),
            },
            "records": (
                int(
                    sum(
                        1
                        for record in records
                        if record.get("progress_support_logging") is not None
                    )
                )
                if args.camp_progress_support_logging
                else 0
            ),
            "latency_ms": (
                {
                    key: _summary(
                        [
                            float(record[key])
                            for record in records
                            if key in record and record[key] is not None
                        ]
                    )
                    for key in PROGRESS_SUPPORT_LATENCY_KEYS
                }
                if args.camp_progress_support_logging
                else None
            ),
            "definition": (
                "current-tick candidate progress-support fields and "
                "nonnegative atom coefficients computed from fixed DP "
                "candidates and current route geometry before closed-loop "
                "outcome labels"
            ),
            "math_boundary": (
                "If later atomized, each progress-support atom is a fixed "
                "finite-candidate coefficient; CAMP score remains affine in "
                "weights and the simplex/CVaR/L2 master remains convex."
            ),
            "classical_benders_claim": False,
        }
        if records is not None
        else None
    )
    camp_lane_hard_violation_support_logging = (
        {
            "schema_version": LANE_HARD_VIOLATION_SUPPORT_LOGGING_SCHEMA_VERSION,
            "enabled": bool(args.camp_lane_hard_violation_support_logging),
            "default_off": True,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "closed_loop_outcome_fields_read": False,
            "online_selector_change": False,
            "authorized_stage": "unit_tests_only_default_off_payload_wiring",
            "logged_field": "lane_hard_violation_support_logging",
            "fields": list(LANE_HARD_VIOLATION_SUPPORT_FIELD_NAMES),
            "atom_names": list(LANE_HARD_VIOLATION_SUPPORT_ATOM_NAMES),
            "latency_fields": list(LANE_HARD_VIOLATION_SUPPORT_LATENCY_KEYS),
            "horizons": {
                "support_steps": int(
                    args.camp_lane_hard_violation_support_steps
                ),
                "dt_s": float(args.camp_lane_hard_violation_support_dt_s),
            },
            "budgets": {
                "corridor_half_width_m": float(
                    args.camp_lane_hard_violation_corridor_half_width_m
                ),
                "lateral_error_rate_budget_mps": float(
                    args.camp_lane_hard_violation_lateral_rate_budget_mps
                ),
            },
            "records": (
                int(
                    sum(
                        1
                        for record in records
                        if record.get("lane_hard_violation_support_logging")
                        is not None
                    )
                )
                if args.camp_lane_hard_violation_support_logging
                else 0
            ),
            "latency_ms": (
                {
                    key: _summary(
                        [
                            float(record[key])
                            for record in records
                            if key in record and record[key] is not None
                        ]
                    )
                    for key in LANE_HARD_VIOLATION_SUPPORT_LATENCY_KEYS
                }
                if args.camp_lane_hard_violation_support_logging
                else None
            ),
            "definition": (
                "current-tick candidate lane/hard-violation support fields "
                "and nonnegative atom coefficients computed from fixed DP "
                "candidates, current route geometry, explicit corridor width, "
                "and planner dt before closed-loop outcome labels"
            ),
            "math_boundary": (
                "If later atomized, each lane/hard-violation support atom is "
                "a fixed finite-candidate coefficient; CAMP score remains "
                "affine in weights and the simplex/CVaR/L2 master remains "
                "convex."
            ),
            "classical_benders_claim": False,
        }
        if records is not None
        else None
    )
    camp_progress_lane_hard_context_logging = (
        {
            "schema_version": PROGRESS_LANE_HARD_CONTEXT_LOGGING_SCHEMA_VERSION,
            "enabled": bool(args.camp_progress_lane_hard_context_logging),
            "default_off": True,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "closed_loop_outcome_fields_read": False,
            "online_selector_change": False,
            "authorized_stage": "unit_tests_only_default_off_payload_wiring",
            "logged_field": "progress_lane_hard_context_logging",
            "fields": list(PROGRESS_LANE_HARD_CONTEXT_FIELD_NAMES),
            "atom_names": list(PROGRESS_LANE_HARD_CONTEXT_ATOM_NAMES),
            "revised_atom_schema_version": (
                PROGRESS_LANE_HARD_CONTEXT_REVISED_ATOM_SCHEMA_VERSION
            ),
            "revised_atom_names": list(PROGRESS_LANE_HARD_CONTEXT_REVISED_ATOM_NAMES),
            "relaxed_strict_atom_schema_version": (
                PROGRESS_LANE_HARD_CONTEXT_RELAXED_STRICT_ATOM_SCHEMA_VERSION
            ),
            "relaxed_strict_atom_names": list(
                PROGRESS_LANE_HARD_CONTEXT_RELAXED_STRICT_ATOM_NAMES
            ),
            "latency_fields": list(PROGRESS_LANE_HARD_CONTEXT_LATENCY_KEYS),
            "horizons": {
                "support_steps": int(
                    args.camp_progress_lane_hard_context_steps
                ),
                "dt_s": float(args.camp_progress_lane_hard_context_dt_s),
            },
            "budgets": {
                "corridor_half_width_m": float(
                    args.camp_progress_lane_hard_context_corridor_half_width_m
                ),
                "corridor_safety_margin_m": float(
                    args.camp_progress_lane_hard_context_corridor_safety_margin_m
                ),
            },
            "records": (
                int(
                    sum(
                        1
                        for record in records
                        if record.get("progress_lane_hard_context_logging")
                        is not None
                    )
                )
                if args.camp_progress_lane_hard_context_logging
                else 0
            ),
            "latency_ms": (
                {
                    key: _summary(
                        [
                            float(record[key])
                            for record in records
                            if key in record and record[key] is not None
                        ]
                    )
                    for key in PROGRESS_LANE_HARD_CONTEXT_LATENCY_KEYS
                }
                if args.camp_progress_lane_hard_context_logging
                else None
            ),
            "definition": (
                "current-tick candidate progress+lane/hard context fields "
                "and nonnegative atom coefficients computed from fixed DP "
                "candidates, current route geometry, explicit corridor width, "
                "and planner dt before closed-loop outcome labels"
            ),
            "math_boundary": (
                "If later atomized, each progress+lane/hard context atom is "
                "a fixed finite-candidate coefficient; CAMP score remains "
                "affine in weights and the simplex/CVaR/L2 master remains "
                "convex."
            ),
            "classical_benders_claim": False,
        }
        if records is not None
        else None
    )
    camp_turn_logit_payload_logging = (
        {
            "schema_version": TURN_LOGIT_PAYLOAD_SCHEMA_VERSION,
            "enabled": bool(args.camp_turn_logit_payload_logging),
            "default_off": True,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "closed_loop_outcome_fields_read": False,
            "online_selector_change": False,
            "authorized_stage": "unit_tests_only_default_off_payload_wiring",
            "logged_field": "turn_logit_payload_logging",
            "fields": list(TURN_LOGIT_PAYLOAD_FIELD_NAMES),
            "atomization_candidate_names": list(
                TURN_LOGIT_PAYLOAD_ATOM_CANDIDATE_NAMES
            ),
            "latency_fields": list(TURN_LOGIT_PAYLOAD_LATENCY_KEYS),
            "records": (
                int(
                    sum(
                        1
                        for record in records
                        if record.get("turn_logit_payload_logging") is not None
                    )
                )
                if args.camp_turn_logit_payload_logging
                else 0
            ),
            "available_records": (
                int(
                    sum(
                        1
                        for record in records
                        if (
                            record.get("turn_logit_payload_logging") is not None
                            and record["turn_logit_payload_logging"].get("available")
                            is True
                        )
                    )
                )
                if args.camp_turn_logit_payload_logging
                else 0
            ),
            "invalid_records": (
                int(
                    sum(
                        1
                        for record in records
                        if (
                            record.get("turn_logit_payload_logging") is not None
                            and not record["turn_logit_payload_logging"]
                            .get("finite_checks", {})
                            .get("payload_valid", False)
                        )
                    )
                )
                if args.camp_turn_logit_payload_logging
                else 0
            ),
            "latency_ms": (
                {
                    key: _summary(
                        [
                            float(record[key])
                            for record in records
                            if key in record and record[key] is not None
                        ]
                    )
                    for key in TURN_LOGIT_PAYLOAD_LATENCY_KEYS
                }
                if args.camp_turn_logit_payload_logging
                else None
            ),
            "definition": (
                "optional current-tick per-candidate turn-indicator logits "
                "returned by the fixed DP wrapper before CAMP selection"
            ),
            "math_boundary": (
                "If later atomized, each turn-logit candidate is a fixed "
                "finite-candidate coefficient; CAMP score remains affine in "
                "weights and the simplex/CVaR/L2 master remains convex."
            ),
            "classical_benders_claim": False,
        }
        if records is not None
        else None
    )
    camp_non_turn_logit_interaction_payload_logging = (
        {
            "schema_version": NON_TURN_LOGIT_INTERACTION_PAYLOAD_SCHEMA_VERSION,
            "enabled": bool(
                args.camp_non_turn_logit_interaction_payload_logging
            ),
            "default_off": True,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "closed_loop_outcome_fields_read": False,
            "online_selector_change": False,
            "deployed_atom_vector_change": False,
            "authorized_stage": "unit_tests_only_default_off_payload_wiring",
            "logged_field": "non_turn_logit_interaction_payload_logging",
            "fields": list(NON_TURN_LOGIT_INTERACTION_PAYLOAD_FIELD_NAMES),
            "diagnostic_field_names": list(
                NON_TURN_LOGIT_INTERACTION_PAYLOAD_DIAGNOSTIC_FIELD_NAMES
            ),
            "atom_candidate_names": list(
                NON_TURN_LOGIT_INTERACTION_PAYLOAD_ATOM_CANDIDATE_NAMES
            ),
            "latency_fields": list(
                NON_TURN_LOGIT_INTERACTION_PAYLOAD_LATENCY_KEYS
            ),
            "records": (
                int(
                    sum(
                        1
                        for record in records
                        if record.get("non_turn_logit_interaction_payload_logging")
                        is not None
                    )
                )
                if args.camp_non_turn_logit_interaction_payload_logging
                else 0
            ),
            "available_records": (
                int(
                    sum(
                        1
                        for record in records
                        if (
                            record.get(
                                "non_turn_logit_interaction_payload_logging"
                            )
                            is not None
                            and record[
                                "non_turn_logit_interaction_payload_logging"
                            ].get("available")
                            is True
                        )
                    )
                )
                if args.camp_non_turn_logit_interaction_payload_logging
                else 0
            ),
            "invalid_records": (
                int(
                    sum(
                        1
                        for record in records
                        if (
                            record.get(
                                "non_turn_logit_interaction_payload_logging"
                            )
                            is not None
                            and not record[
                                "non_turn_logit_interaction_payload_logging"
                            ]
                            .get("finite_checks", {})
                            .get("payload_valid", False)
                        )
                    )
                )
                if args.camp_non_turn_logit_interaction_payload_logging
                else 0
            ),
            "latency_ms": (
                {
                    key: _summary(
                        [
                            float(record[key])
                            for record in records
                            if key in record and record[key] is not None
                        ]
                    )
                    for key in NON_TURN_LOGIT_INTERACTION_PAYLOAD_LATENCY_KEYS
                }
                if args.camp_non_turn_logit_interaction_payload_logging
                else None
            ),
            "definition": (
                "current-tick progress/comfort interaction diagnostics "
                "computed from fixed DP candidate route progress and "
                "DP-prior jerk-excess costs before selection"
            ),
            "math_boundary": (
                "If later atomized, comfort_progress_interaction_cost is a "
                "fixed nonnegative finite-candidate coefficient; CAMP score "
                "remains affine in weights and the simplex/CVaR/L2 master "
                "remains convex. Existing progress and jerk fields remain "
                "diagnostic-only in this payload."
            ),
            "classical_benders_claim": False,
        }
        if records is not None
        else None
    )
    camp_external_context_payload_logging = (
        {
            "schema_version": EXTERNAL_CONTEXT_PAYLOAD_SCHEMA_VERSION,
            "enabled": bool(args.camp_external_context_payload_logging),
            "default_off": True,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "closed_loop_outcome_fields_read": False,
            "online_selector_change": False,
            "deployed_atom_vector_change": False,
            "authorized_stage": "unit_tests_only_default_off_payload_wiring",
            "logged_field": "external_context_payload_logging",
            "fields": list(EXTERNAL_CONTEXT_PAYLOAD_FIELD_NAMES),
            "atom_candidate_names": list(
                EXTERNAL_CONTEXT_PAYLOAD_ATOM_CANDIDATE_NAMES
            ),
            "latency_fields": list(EXTERNAL_CONTEXT_PAYLOAD_LATENCY_KEYS),
            "records": (
                int(
                    sum(
                        1
                        for record in records
                        if record.get("external_context_payload_logging")
                        is not None
                    )
                )
                if args.camp_external_context_payload_logging
                else 0
            ),
            "available_records": (
                int(
                    sum(
                        1
                        for record in records
                        if (
                            record.get("external_context_payload_logging")
                            is not None
                            and record["external_context_payload_logging"].get(
                                "available"
                            )
                            is True
                        )
                    )
                )
                if args.camp_external_context_payload_logging
                else 0
            ),
            "invalid_records": (
                int(
                    sum(
                        1
                        for record in records
                        if (
                            record.get("external_context_payload_logging")
                            is not None
                            and not record["external_context_payload_logging"]
                            .get("finite_checks", {})
                            .get("payload_valid", False)
                        )
                    )
                )
                if args.camp_external_context_payload_logging
                else 0
            ),
            "latency_ms": (
                {
                    key: _summary(
                        [
                            float(record[key])
                            for record in records
                            if key in record and record[key] is not None
                        ]
                    )
                    for key in EXTERNAL_CONTEXT_PAYLOAD_LATENCY_KEYS
                }
                if args.camp_external_context_payload_logging
                else None
            ),
            "definition": (
                "default-off current-tick traffic-signal and route speed-limit "
                "context diagnostics computed from fixed DP candidates and "
                "explicit pre-selection context"
            ),
            "math_boundary": (
                "External-context fields are fixed finite-candidate "
                "coefficients or fail-closed diagnostics. If later atomized "
                "after a separate gate, CAMP score remains affine in weights "
                "and the simplex/CVaR/L2 master remains convex. No DP-side "
                "classical Benders claim is made."
            ),
            "classical_benders_claim": False,
        }
        if records is not None
        else None
    )
    camp_temporal_consistency_payload_logging = (
        {
            "schema_version": TEMPORAL_CONSISTENCY_PAYLOAD_SCHEMA_VERSION,
            "enabled": bool(args.camp_temporal_consistency_payload_logging),
            "default_off": True,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "closed_loop_outcome_fields_read": False,
            "online_selector_change": False,
            "deployed_atom_vector_change": False,
            "authorized_stage": (
                "default_off_temporal_consistency_payload_runtime_preflight_only"
            ),
            "logged_field": "temporal_consistency_payload_logging",
            "fields": list(TEMPORAL_CONSISTENCY_PAYLOAD_FIELD_NAMES),
            "atom_candidate_names": list(
                TEMPORAL_CONSISTENCY_PAYLOAD_ATOM_CANDIDATE_NAMES
            ),
            "latency_fields": list(TEMPORAL_CONSISTENCY_PAYLOAD_LATENCY_KEYS),
            "records": (
                int(
                    sum(
                        1
                        for record in records
                        if record.get("temporal_consistency_payload_logging")
                        is not None
                    )
                )
                if args.camp_temporal_consistency_payload_logging
                else 0
            ),
            "available_records": (
                int(
                    sum(
                        1
                        for record in records
                        if (
                            record.get("temporal_consistency_payload_logging")
                            is not None
                            and record[
                                "temporal_consistency_payload_logging"
                            ].get("available")
                            is True
                        )
                    )
                )
                if args.camp_temporal_consistency_payload_logging
                else 0
            ),
            "invalid_records": (
                int(
                    sum(
                        1
                        for record in records
                        if (
                            record.get("temporal_consistency_payload_logging")
                            is not None
                            and not record[
                                "temporal_consistency_payload_logging"
                            ]
                            .get("finite_checks", {})
                            .get("payload_valid", False)
                        )
                    )
                )
                if args.camp_temporal_consistency_payload_logging
                else 0
            ),
            "first_tick_fail_closed_records": (
                int(
                    sum(
                        1
                        for record in records
                        if (
                            record.get("temporal_consistency_payload_logging")
                            is not None
                            and record[
                                "temporal_consistency_payload_logging"
                            ].get("availability_reason")
                            == "previous_selected_plan_absent"
                        )
                    )
                )
                if args.camp_temporal_consistency_payload_logging
                else 0
            ),
            "latency_ms": (
                {
                    key: _summary(
                        [
                            float(record[key])
                            for record in records
                            if key in record and record[key] is not None
                        ]
                    )
                    for key in TEMPORAL_CONSISTENCY_PAYLOAD_LATENCY_KEYS
                }
                if args.camp_temporal_consistency_payload_logging
                else None
            ),
            "definition": (
                "default-off current-tick candidate RMS deviation from the "
                "previous tick selected planned trajectory after shifting by "
                "elapsed planner samples"
            ),
            "math_boundary": (
                "The temporal consistency field is a fixed finite-candidate "
                "coefficient when available and is nonnegative by construction. "
                "Missing previous-plan memory fails closed. If later atomized "
                "after a separate gate, CAMP score remains affine in weights "
                "and the simplex/CVaR/L2 master remains convex. No DP-side "
                "classical Benders claim is made."
            ),
            "classical_benders_claim": False,
        }
        if records is not None
        else None
    )
    finite_candidate_contract = _dp_camp_finite_candidate_contract(
        selector_mode=args.camp_selector_mode,
        num_candidates=args.num_candidates,
        feasibility_source=args.camp_feasibility_source,
        fallback_mode=args.camp_fallback_mode,
        atom_clip=args.camp_atom_clip,
    )
    effective_splice_shadow_rule = _summarize_splice_shadow_rule_records(
        records,
        enabled=bool(args.camp_splice_shadow_rule),
        anchor_steps=args.camp_splice_shadow_anchor_steps,
        blend_steps=args.camp_splice_shadow_blend_steps,
        heading_mode=args.camp_splice_shadow_heading_mode,
        progress_loss_budget_m=args.camp_splice_shadow_progress_loss_budget_m,
        smoothness_loss_budget=args.camp_splice_shadow_smoothness_loss_budget,
    )
    effective_traffic_light_hybrid_postselection = (
        _summarize_traffic_light_hybrid_postselection_records(
            records,
            mode=args.camp_traffic_light_hybrid_postselection,
        )
    )
    summary = {
        "replay_result": result,
        "camp_selection_log": str(selection_log) if selection_log is not None else None,
        "camp_metric_log": str(metric_log),
        "camp_evaluation_state_log": str(evaluation_log),
        "num_candidates": effective_num_candidates,
        "candidate_noise_scale": effective_noise_scale,
        "candidate_reference_blend": effective_reference_blend,
        "candidate_generation_contract": (
            candidate_generation_contract
            if records is not None
            else None
        ),
        "dp_camp_finite_candidate_contract": finite_candidate_contract,
        "camp_microbenchmark_snapshots": (
            {
                "enabled": True,
                "selection_effect": False,
                "latency_evidence": False,
                "directory": str(args.camp_microbenchmark_snapshot_dir),
                "requested_steps": list(
                    args.camp_microbenchmark_snapshot_steps
                ),
                "files": [str(path) for path in microbenchmark_snapshot_paths],
            }
            if args.camp_microbenchmark_snapshot_dir is not None
            else None
        ),
        "camp_raw_candidate_prefix_logging": camp_raw_candidate_prefix_logging,
        "camp_observable_state_logging": camp_observable_state_logging,
        "camp_red_route_vector_logging": camp_red_route_vector_logging,
        "camp_progress_support_logging": camp_progress_support_logging,
        "camp_lane_hard_violation_support_logging": (
            camp_lane_hard_violation_support_logging
        ),
        "camp_progress_lane_hard_context_logging": (
            camp_progress_lane_hard_context_logging
        ),
        "camp_turn_logit_payload_logging": camp_turn_logit_payload_logging,
        "camp_non_turn_logit_interaction_payload_logging": (
            camp_non_turn_logit_interaction_payload_logging
        ),
        "camp_external_context_payload_logging": (
            camp_external_context_payload_logging
        ),
        "camp_temporal_consistency_payload_logging": (
            camp_temporal_consistency_payload_logging
        ),
        "camp_splice_shadow_rule": effective_splice_shadow_rule,
        "camp_traffic_light_hybrid_postselection": (
            effective_traffic_light_hybrid_postselection
        ),
        "camp_lane_corridor_buffer": effective_lane_buffer,
        "camp_feasibility_source": effective_feasibility_source,
        "camp_min_progress_ratio": effective_min_progress_ratio,
        "camp_min_candidate0_progress_ratio": (
            effective_min_candidate0_progress_ratio
        ),
        "camp_min_candidate0_route_progress_ratio": (
            effective_min_candidate0_route_progress_ratio
        ),
        "camp_shadow_route_progress": {
            "enabled": effective_shadow_route_progress,
            "selection_effect": False,
            "logged_field": "candidate_route_progress",
        }
        if effective_shadow_route_progress is not None
        else None,
        "camp_shadow_obstacle_clearance": {
            "enabled": effective_shadow_obstacle_clearance,
            "selection_effect": False,
            "future_outcome_leakage": False,
            "logged_field": "candidate_obstacle_clearance",
            "descriptor_schema": "candidate_current_tick_obstacle_clearance_v2",
            "definition": (
                "current-tick candidate trajectory versus current-tick "
                "predicted/static obstacle geometry; reports conservative "
                "clearance lower-bound hinges and can optionally report "
                "near-threshold exact OBB diagnostics"
            ),
            "exact_obb_enabled": bool(
                args.camp_shadow_obstacle_clearance_exact_obb
            ),
            "soft_clearance_threshold_m": (
                float(args.camp_safety_radius + args.camp_clearance_margin)
            ),
            "near_miss_threshold_m": float(args.near_miss_threshold_m),
            "requested_horizon_steps": int(args.camp_outcome_horizon_steps),
        }
        if effective_shadow_obstacle_clearance is not None
        else None,
        "camp_min_candidate0_step_reach_ratio": (
            effective_min_candidate0_step_reach_ratio
        ),
        "camp_candidate0_step_reach_preserve_feasible": (
            effective_candidate0_step_reach_preserve_feasible
        ),
        "camp_lexicographic_preselection": effective_lexicographic_preselection,
        "camp_perfect_tracker_command_postselection": (
            effective_perfect_tracker_command_postselection
        ),
        "camp_underprogress_relaxation": effective_underprogress_relaxation,
        "camp_reward_horizon_steps": effective_reward_horizon_steps,
        "camp_collect_closed_loop_outcomes": (
            bool(args.camp_collect_closed_loop_outcomes)
            if records is not None
            else None
        ),
        "camp_outcome_horizon_steps": (
            args.camp_outcome_horizon_steps
            if records is not None and args.camp_collect_closed_loop_outcomes
            else None
        ),
        "camp_shadow_red_stopping_margin": (
            {
                "enabled": True,
                "selection_effect": False,
                "comfort_deceleration_mps2": 2.0,
                "stop_buffer_m": 3.0,
                "lookahead_m": 40.0,
                "heading_alignment_threshold": 0.5,
                "unit": "m^2/s",
            }
            if records is not None
            else None
        ),
        "camp_shadow_dp_prior_comfort_excess": (
            {
                "enabled": True,
                "selection_effect": False,
                "reference_candidate_index": 0,
                "requested_horizon_steps": args.camp_outcome_horizon_steps,
                "effective_horizon_steps": (
                    effective_comfort_shadow_horizon_steps
                ),
                "definition": (
                    "positive mean finite-difference jerk/acceleration "
                    "norm excess over candidate 0"
                ),
            }
            if records is not None
            else None
        ),
        "camp_shadow_lateral_comfort": (
            {
                "enabled": True,
                "selection_effect": False,
                "reference_candidate_index": 0,
                "requested_horizon_steps": args.camp_outcome_horizon_steps,
                "effective_horizon_steps": (
                    effective_lateral_comfort_horizon_steps
                ),
                "fields": [
                    "candidate_horizon_lateral_acceleration_cost",
                    "candidate_dp_prior_lateral_acceleration_excess_cost",
                    "candidate_horizon_yaw_rate_cost",
                    "candidate_dp_prior_yaw_rate_excess_cost",
                ],
            }
            if records is not None
            else None
        ),
        "camp_shadow_perfect_tracker_command": (
            {
                "schema_version": "perfect_tracker_command_shadow_v2",
                "enabled": True,
                "selection_effect": False,
                "tracker_class": (
                    "scenario_generation.mpc_tracker.PerfectTracker"
                ),
                "reference_postprocessing": (
                    "scenario_generation.mpc_tracker.postprocess_reference"
                ),
                "candidate_frame": "ego",
                "candidate_preprocessing": (
                    _perfect_tracker_candidate_preprocessing(config)
                ),
                "max_speed_mps": 20.0,
                "velocity_smooth_window": 8,
                "stop_threshold_mps": 0.3,
                "restart_speed_threshold_mps": 0.1,
                "restart_plan_speed_threshold_mps": 0.5,
                "fields": [
                    "candidate_perfect_tracker_reference_first_xy",
                    (
                        "candidate_perfect_tracker_"
                        "reference_first_heading_rad"
                    ),
                    "candidate_perfect_tracker_first_step_reach_m",
                    "candidate_perfect_tracker_tail_average_speed_mps",
                    "candidate_perfect_tracker_restart_push",
                    "candidate_perfect_tracker_target_speed_mps",
                    "candidate_perfect_tracker_acceleration_mps2",
                    "candidate_perfect_tracker_jerk_magnitude_mps3",
                    "candidate_perfect_tracker_yaw_rate_magnitude_rps",
                    (
                        "candidate_perfect_tracker_"
                        "lateral_acceleration_magnitude_mps2"
                    ),
                ],
            }
            if records is not None
            else None
        ),
        "camp_shadow_perfect_tracker_open_loop_rollout": (
            {
                "schema_version": "perfect_tracker_open_loop_rollout_v1",
                "enabled": True,
                "selection_effect": False,
                "online_feature_eligible": True,
                "closed_loop_guarantee": False,
                "tracker_class": (
                    "scenario_generation.mpc_tracker.PerfectTracker"
                ),
                "reference_postprocessing": (
                    "scenario_generation.mpc_tracker.postprocess_reference"
                ),
                "candidate_preprocessing": (
                    _perfect_tracker_candidate_preprocessing(config)
                ),
                "candidate_frame": "ego",
                "horizons": list(PERFECT_TRACKER_OPEN_LOOP_HORIZONS),
                "definition": (
                    "fixed-candidate PerfectTracker commit rollout without "
                    "Diffusion Planner replanning"
                ),
                "metrics": [
                    "distance_m",
                    "mean_vector_jerk_mps3",
                    "max_vector_jerk_mps3",
                    "mean_lateral_acceleration_mps2",
                    "max_lateral_acceleration_mps2",
                ],
            }
            if records is not None
            else None
        ),
        "camp_shadow_full_horizon_red_light": (
            {
                "schema_version": "full_horizon_red_light_shadow_v1",
                "enabled": True,
                "selection_effect": False,
                "online_feature_eligible": True,
                "source": "rlvr.reward.compute_red_light_score_batch",
                "candidate_preprocessing": (
                    _perfect_tracker_candidate_preprocessing(config)
                ),
                "candidate_frame": "ego",
                "horizon_steps": (
                    records[0][
                        "candidate_full_horizon_red_light_horizon_steps"
                    ]
                    if records
                    else None
                ),
                "raw_full_horizon_field": (
                    "candidate_full_horizon_planned_red_light_cost"
                ),
                "horizon_union_certificate_field": (
                    "candidate_horizon_union_planned_red_light_cost"
                ),
            }
            if records is not None
            and args.camp_feasibility_source == "dp_reward"
            else None
        ),
        "selector_mode": args.camp_selector_mode,
        "camp_fallback_mode": args.camp_fallback_mode,
        "advance_mode": config.advance_mode,
        "dp_scene_feature_names": list(DP_SCENE_FEATURE_NAMES),
        "model_args": str(args.model_args) if args.model_args is not None else None,
        "using_no_ros_projection_fallback": using_projection_fallback,
        "benchmark": {
            "variant": args.camp_selector_mode,
            "fallback_mode": args.camp_fallback_mode,
            "route": str(args.route),
            "map_path": str(map_path),
            "model_path": str(args.model_path),
            "config": str(args.config),
            "seed": args.seed,
            "steps": args.steps,
            "max_npcs": args.max_npcs,
            "spawn_probability": args.spawn_probability,
            "traffic_lights": bool(config.enable_traffic_lights),
            "advance_mode": config.advance_mode,
            "reward_config": (
                str(args.reward_config) if args.reward_config is not None else None
            ),
        },
    }
    (args.output_dir / "camp_replay_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    validation = summarize_replay_artifacts(
        args.output_dir,
        selection_records=records,
        replay_result=result,
        metric_records=metric_records,
        evaluation_records=evaluation_records,
        route_centerline=_route_centerline_world(builder, route),
        near_miss_threshold_m=args.near_miss_threshold_m,
    )
    validation["selector_mode"] = args.camp_selector_mode
    validation["num_candidates"] = effective_num_candidates
    validation["candidate_noise_scale"] = effective_noise_scale
    validation["candidate_reference_blend"] = effective_reference_blend
    validation["camp_lane_corridor_buffer"] = effective_lane_buffer
    validation["camp_feasibility_source"] = effective_feasibility_source
    validation["camp_min_progress_ratio"] = effective_min_progress_ratio
    validation["camp_min_candidate0_progress_ratio"] = (
        effective_min_candidate0_progress_ratio
    )
    validation["camp_min_candidate0_route_progress_ratio"] = (
        effective_min_candidate0_route_progress_ratio
    )
    validation["camp_shadow_route_progress"] = summary["camp_shadow_route_progress"]
    validation["camp_shadow_obstacle_clearance"] = summary[
        "camp_shadow_obstacle_clearance"
    ]
    validation["camp_min_candidate0_step_reach_ratio"] = (
        effective_min_candidate0_step_reach_ratio
    )
    validation["camp_candidate0_step_reach_preserve_feasible"] = (
        effective_candidate0_step_reach_preserve_feasible
    )
    validation["camp_lexicographic_preselection"] = (
        effective_lexicographic_preselection
    )
    validation["camp_perfect_tracker_command_postselection"] = (
        effective_perfect_tracker_command_postselection
    )
    validation["camp_underprogress_relaxation"] = effective_underprogress_relaxation
    validation["camp_microbenchmark_snapshots"] = summary[
        "camp_microbenchmark_snapshots"
    ]
    validation["camp_raw_candidate_prefix_logging"] = (
        camp_raw_candidate_prefix_logging
    )
    validation["camp_observable_state_logging"] = camp_observable_state_logging
    validation["camp_red_route_vector_logging"] = camp_red_route_vector_logging
    validation["camp_progress_support_logging"] = camp_progress_support_logging
    validation["camp_lane_hard_violation_support_logging"] = (
        camp_lane_hard_violation_support_logging
    )
    validation["camp_progress_lane_hard_context_logging"] = (
        camp_progress_lane_hard_context_logging
    )
    validation["camp_turn_logit_payload_logging"] = camp_turn_logit_payload_logging
    validation["camp_non_turn_logit_interaction_payload_logging"] = (
        camp_non_turn_logit_interaction_payload_logging
    )
    validation["camp_external_context_payload_logging"] = (
        camp_external_context_payload_logging
    )
    validation["camp_temporal_consistency_payload_logging"] = (
        camp_temporal_consistency_payload_logging
    )
    validation["camp_splice_shadow_rule"] = effective_splice_shadow_rule
    validation["camp_traffic_light_hybrid_postselection"] = (
        effective_traffic_light_hybrid_postselection
    )
    validation["camp_reward_horizon_steps"] = effective_reward_horizon_steps
    validation["camp_collect_closed_loop_outcomes"] = (
        bool(args.camp_collect_closed_loop_outcomes) if records is not None else None
    )
    validation["camp_outcome_horizon_steps"] = (
        args.camp_outcome_horizon_steps
        if records is not None and args.camp_collect_closed_loop_outcomes
        else None
    )
    validation["camp_shadow_dp_prior_comfort_excess"] = summary[
        "camp_shadow_dp_prior_comfort_excess"
    ]
    validation["camp_shadow_lateral_comfort"] = summary[
        "camp_shadow_lateral_comfort"
    ]
    validation["camp_shadow_perfect_tracker_command"] = summary[
        "camp_shadow_perfect_tracker_command"
    ]
    validation["camp_shadow_perfect_tracker_open_loop_rollout"] = summary[
        "camp_shadow_perfect_tracker_open_loop_rollout"
    ]
    validation["camp_shadow_full_horizon_red_light"] = summary[
        "camp_shadow_full_horizon_red_light"
    ]
    _copy_replay_contract_metadata_to_validation(validation, summary)
    validation["benchmark"] = summary["benchmark"]
    validation["benchmark_key"] = (
        f"route={args.route}|seed={args.seed}|steps={args.steps}|"
        f"max_npcs={args.max_npcs}|spawn_probability={args.spawn_probability}|"
        f"traffic_lights={bool(config.enable_traffic_lights)}|"
        f"advance_mode={config.advance_mode}"
    )
    validation["camp_fallback_mode"] = args.camp_fallback_mode
    validation["advance_mode"] = config.advance_mode
    (args.output_dir / "camp_validation_summary.json").write_text(
        json.dumps(validation, indent=2), encoding="utf-8"
    )
    print(json.dumps({"replay": summary, "validation": validation}, indent=2))


if __name__ == "__main__":
    main()
