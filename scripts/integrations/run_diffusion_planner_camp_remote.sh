#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CAMP_ROOT="${CAMP_ROOT:-$(cd -- "$SCRIPT_DIR/../.." && pwd)}"
DIFFUSION_REPO="${DIFFUSION_REPO:-/root/autodl-tmp/Diffusion-Planner}"
DP_MODEL="${DP_MODEL:-}"
DP_MODEL_ARGS="${DP_MODEL_ARGS:-}"
ROUTE="${ROUTE:-}"
SPAWN_CONFIG="${SPAWN_CONFIG:-$DIFFUSION_REPO/scenario_generation/configs/replay_default.json}"
REWARD_CONFIG="${REWARD_CONFIG:-$CAMP_ROOT/configs/integrations/dp_camp_reward_eval.json}"
CAMP_CHECKPOINT="${CAMP_CHECKPOINT:-}"
CAMP_STATIC_WEIGHTS="${CAMP_STATIC_WEIGHTS:-}"
CAMP_SELECTOR_MODE="${CAMP_SELECTOR_MODE:-static}"
CAMP_FALLBACK_MODE="${CAMP_FALLBACK_MODE:-uniform}"
CAMP_ATOM_SCALES="${CAMP_ATOM_SCALES:-}"
OUTPUT_DIR="${OUTPUT_DIR:-/root/autodl-tmp/camp_dp_replay_smoke}"
MAP_PATH="${MAP_PATH:-}"
STEPS="${STEPS:-20}"
NUM_CANDIDATES="${NUM_CANDIDATES:-8}"
CANDIDATE_NOISE_SCALE="${CANDIDATE_NOISE_SCALE:-1.0}"
CANDIDATE_NOISE_STRATEGY="${CANDIDATE_NOISE_STRATEGY:-iid}"
CANDIDATE_GUIDANCE_CONFIG="${CANDIDATE_GUIDANCE_CONFIG:-}"
CANDIDATE_GUIDANCE_SCALE="${CANDIDATE_GUIDANCE_SCALE:-}"
CAMP_LOG_RAW_CANDIDATE_PREFIX_STEPS="${CAMP_LOG_RAW_CANDIDATE_PREFIX_STEPS:-0}"
CAMP_FEASIBILITY_SOURCE="${CAMP_FEASIBILITY_SOURCE:-dp_reward}"
CAMP_MIN_PROGRESS_RATIO="${CAMP_MIN_PROGRESS_RATIO:-0.8}"
CAMP_REWARD_HORIZON_STEPS="${CAMP_REWARD_HORIZON_STEPS:-30}"
CAMP_COLLECT_CLOSED_LOOP_OUTCOMES="${CAMP_COLLECT_CLOSED_LOOP_OUTCOMES:-0}"
CAMP_OUTCOME_HORIZON_STEPS="${CAMP_OUTCOME_HORIZON_STEPS:-30}"
CAMP_OUTCOME_PROGRESS_WEIGHT="${CAMP_OUTCOME_PROGRESS_WEIGHT:-1.0}"
CAMP_OUTCOME_COLLISION_PENALTY="${CAMP_OUTCOME_COLLISION_PENALTY:-100.0}"
CAMP_OUTCOME_NEAR_MISS_PENALTY="${CAMP_OUTCOME_NEAR_MISS_PENALTY:-10.0}"
CAMP_OUTCOME_LANE_PENALTY="${CAMP_OUTCOME_LANE_PENALTY:-20.0}"
CAMP_OUTCOME_RED_LIGHT_PENALTY="${CAMP_OUTCOME_RED_LIGHT_PENALTY:-30.0}"
CAMP_OUTCOME_JERK_PENALTY="${CAMP_OUTCOME_JERK_PENALTY:-0.25}"
CAMP_OUTCOME_LATERAL_ACCELERATION_PENALTY="${CAMP_OUTCOME_LATERAL_ACCELERATION_PENALTY:-1.0}"
DEVICE="${DEVICE:-cuda}"
SEED="${SEED:-42}"
MAX_NPCS="${MAX_NPCS:-8}"
SPAWN_PROBABILITY="${SPAWN_PROBABILITY:-0.3}"
REPLAY_NO_PNG="${REPLAY_NO_PNG:-1}"
DP_PYTHON="${DP_PYTHON:-}"

fail() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

require_file() {
  [[ -f "$1" ]] || fail "$2 not found: $1"
}

require_dir() {
  [[ -d "$1" ]] || fail "$2 not found: $1"
}

require_dir "$CAMP_ROOT" "CAMP checkout"
require_dir "$DIFFUSION_REPO" "Diffusion-Planner checkout"
require_file "$DP_MODEL" "Diffusion Planner model"
if [[ -n "$DP_MODEL_ARGS" ]]; then
  require_file "$DP_MODEL_ARGS" "Diffusion Planner parameter JSON"
fi
require_file "$ROUTE" "saved Route"
require_file "$SPAWN_CONFIG" "spawn config"
require_file "$CAMP_ATOM_SCALES" "CAMP atom scales"
if [[ -n "$CANDIDATE_GUIDANCE_CONFIG" ]]; then
  require_file "$CANDIDATE_GUIDANCE_CONFIG" "candidate guidance config"
fi
if [[ "$CAMP_FEASIBILITY_SOURCE" == "dp_reward" ]]; then
  require_file "$REWARD_CONFIG" "reward config"
fi
if [[ "$CAMP_SELECTOR_MODE" != "static" && "$CAMP_SELECTOR_MODE" != "linear" ]]; then
  fail "CAMP_SELECTOR_MODE must be static or linear"
fi
if [[ "$CAMP_FALLBACK_MODE" != "uniform" && "$CAMP_FALLBACK_MODE" != "learned" ]]; then
  fail "CAMP_FALLBACK_MODE must be uniform or learned"
fi

if [[ -n "$DP_PYTHON" ]]; then
  require_file "$DP_PYTHON" "Diffusion Planner Python"
  DP_RUN=("$DP_PYTHON")
elif command -v uv >/dev/null 2>&1; then
  DP_RUN=(uv run --project "$DIFFUSION_REPO" python)
elif [[ -x "$DIFFUSION_REPO/.venv/bin/python" ]]; then
  DP_RUN=("$DIFFUSION_REPO/.venv/bin/python")
else
  fail "set DP_PYTHON, install uv, or create DIFFUSION_REPO/.venv"
fi

if [[ -n "$CAMP_CHECKPOINT" && -n "$CAMP_STATIC_WEIGHTS" ]]; then
  fail "set only one of CAMP_CHECKPOINT or CAMP_STATIC_WEIGHTS"
fi
if [[ -n "$CAMP_CHECKPOINT" ]]; then
  require_file "$CAMP_CHECKPOINT" "CAMP checkpoint"
  CAMP_WEIGHT_ARGS=(--camp_checkpoint "$CAMP_CHECKPOINT")
elif [[ -n "$CAMP_STATIC_WEIGHTS" ]]; then
  require_file "$CAMP_STATIC_WEIGHTS" "CAMP static weights"
  CAMP_WEIGHT_ARGS=(--camp_static_weights "$CAMP_STATIC_WEIGHTS")
else
  fail "set CAMP_CHECKPOINT or CAMP_STATIC_WEIGHTS"
fi

if [[ -e "$OUTPUT_DIR/camp_replay_summary.json" ]]; then
  fail "output already contains a CAMP replay; choose a new OUTPUT_DIR: $OUTPUT_DIR"
fi
mkdir -p "$OUTPUT_DIR"

EFFECTIVE_CONFIG="$OUTPUT_DIR/camp_spawn_config.json"
"${DP_RUN[@]}" - "$SPAWN_CONFIG" "$EFFECTIVE_CONFIG" <<'PY'
import json
import sys
from pathlib import Path

source = Path(sys.argv[1])
target = Path(sys.argv[2])
config = json.loads(source.read_text(encoding="utf-8"))
config["advance_mode"] = "perfect"
target.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
PY

DP_COMMIT="$(git -C "$DIFFUSION_REPO" rev-parse HEAD 2>/dev/null || printf 'unknown')"
printf 'CAMP_ROOT=%s\n' "$CAMP_ROOT"
printf 'DIFFUSION_REPO=%s\n' "$DIFFUSION_REPO"
printf 'DIFFUSION_COMMIT=%s\n' "$DP_COMMIT"
printf 'OUTPUT_DIR=%s\n' "$OUTPUT_DIR"

"${DP_RUN[@]}" - "$DIFFUSION_REPO" "$DEVICE" <<'PY'
import sys
from pathlib import Path

repo = Path(sys.argv[1]).resolve()
sys.path[:0] = [str(repo), str(repo / "diffusion_planner")]

import torch
import scenario_generation.replay as replay
import scenario_generation.tensor_converter as tensor_converter

required = ["_predict_batch", "run_route_replay", "load_model"]
missing = [name for name in required if not hasattr(replay, name)]
if missing or not hasattr(tensor_converter, "to_model_tensors"):
    raise RuntimeError(f"unsupported Diffusion-Planner replay API; missing={missing}")

device = sys.argv[2]
print(f"python={sys.version.split()[0]}")
print(f"torch={torch.__version__}")
print(f"cuda_available={torch.cuda.is_available()}")
if device.startswith("cuda") and not torch.cuda.is_available():
    raise RuntimeError("DEVICE requests CUDA, but torch.cuda.is_available() is false")
if torch.cuda.is_available():
    print(f"gpu={torch.cuda.get_device_name(0)}")
PY

RUN_ARGS=(
  --diffusion_repo "$DIFFUSION_REPO"
  --route "$ROUTE"
  --model_path "$DP_MODEL"
  --config "$EFFECTIVE_CONFIG"
  --output_dir "$OUTPUT_DIR"
  --camp_atom_scales "$CAMP_ATOM_SCALES"
  --camp_selector_mode "$CAMP_SELECTOR_MODE"
  --camp_fallback_mode "$CAMP_FALLBACK_MODE"
  --num_candidates "$NUM_CANDIDATES"
  --candidate_noise_scale "$CANDIDATE_NOISE_SCALE"
  --candidate_noise_strategy "$CANDIDATE_NOISE_STRATEGY"
  --camp_log_raw_candidate_prefix_steps "$CAMP_LOG_RAW_CANDIDATE_PREFIX_STEPS"
  --camp_feasibility_source "$CAMP_FEASIBILITY_SOURCE"
  --camp_min_progress_ratio "$CAMP_MIN_PROGRESS_RATIO"
  --camp_reward_horizon_steps "$CAMP_REWARD_HORIZON_STEPS"
  --steps "$STEPS"
  --device "$DEVICE"
  --seed "$SEED"
  --max_npcs "$MAX_NPCS"
  --spawn_probability "$SPAWN_PROBABILITY"
)
RUN_ARGS+=("${CAMP_WEIGHT_ARGS[@]}")
if [[ -n "$CANDIDATE_GUIDANCE_CONFIG" ]]; then
  RUN_ARGS+=(--candidate_guidance_config "$CANDIDATE_GUIDANCE_CONFIG")
fi
if [[ -n "$CANDIDATE_GUIDANCE_SCALE" ]]; then
  RUN_ARGS+=(--candidate_guidance_scale "$CANDIDATE_GUIDANCE_SCALE")
fi
if [[ "$CAMP_COLLECT_CLOSED_LOOP_OUTCOMES" == "1" ]]; then
  RUN_ARGS+=(
    --camp_collect_closed_loop_outcomes
    --camp_outcome_horizon_steps "$CAMP_OUTCOME_HORIZON_STEPS"
    --camp_outcome_progress_weight "$CAMP_OUTCOME_PROGRESS_WEIGHT"
    --camp_outcome_collision_penalty "$CAMP_OUTCOME_COLLISION_PENALTY"
    --camp_outcome_near_miss_penalty "$CAMP_OUTCOME_NEAR_MISS_PENALTY"
    --camp_outcome_lane_penalty "$CAMP_OUTCOME_LANE_PENALTY"
    --camp_outcome_red_light_penalty "$CAMP_OUTCOME_RED_LIGHT_PENALTY"
    --camp_outcome_jerk_penalty "$CAMP_OUTCOME_JERK_PENALTY"
    --camp_outcome_lateral_acceleration_penalty "$CAMP_OUTCOME_LATERAL_ACCELERATION_PENALTY"
  )
fi
if [[ -n "$REWARD_CONFIG" ]]; then
  RUN_ARGS+=(--reward_config "$REWARD_CONFIG")
fi
if [[ -n "$DP_MODEL_ARGS" ]]; then
  RUN_ARGS+=(--model_args "$DP_MODEL_ARGS")
fi
if [[ -n "$MAP_PATH" ]]; then
  require_file "$MAP_PATH" "map override"
  RUN_ARGS+=(--map_path "$MAP_PATH")
fi

export REPLAY_NO_PNG
export PYTHONUNBUFFERED=1
"${DP_RUN[@]}" \
  "$CAMP_ROOT/scripts/integrations/run_diffusion_planner_camp_replay.py" \
  "${RUN_ARGS[@]}"

"${DP_RUN[@]}" \
  "$CAMP_ROOT/scripts/integrations/summarize_diffusion_planner_camp_replay.py" \
  --output_dir "$OUTPUT_DIR"
