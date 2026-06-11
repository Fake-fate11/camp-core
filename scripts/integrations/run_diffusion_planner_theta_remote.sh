#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CAMP_ROOT="${CAMP_ROOT:-$(cd -- "$SCRIPT_DIR/../.." && pwd)}"
DP_PYTHON="${DP_PYTHON:-/root/autodl-tmp/dp312_venv/bin/python}"
THETA_OUTPUT_DIR="${THETA_OUTPUT_DIR:-/root/autodl-tmp/camp_dp_assets/camp_dp_scene_theta_v1}"
SELECTION_LOGS="${SELECTION_LOGS:-}"
EPOCHS="${EPOCHS:-1000}"
LR="${LR:-0.01}"
L2_REG="${L2_REG:-0.0001}"
VAL_FRACTION="${VAL_FRACTION:-0.2}"
FEATURE_CLIP="${FEATURE_CLIP:-5.0}"
SCALE_PERCENTILE="${SCALE_PERCENTILE:-95.0}"
SEED="${SEED:-7}"
LABEL_SOURCE="${LABEL_SOURCE:-dp_reward}"
REWARD_KEY="${REWARD_KEY:-quality_without_progress}"
REWARD_PROGRESS_WEIGHT="${REWARD_PROGRESS_WEIGHT:-2.0}"
BACKGROUND="${BACKGROUND:-0}"

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
require_file "$DP_PYTHON" "Diffusion Planner Python"
[[ -n "$SELECTION_LOGS" ]] || fail "set SELECTION_LOGS to a colon-separated list of camp_selection_log.json files"

IFS=':' read -r -a LOG_PATHS <<< "$SELECTION_LOGS"
LOG_ARGS=()
for log_path in "${LOG_PATHS[@]}"; do
  require_file "$log_path" "selection log"
  LOG_ARGS+=(--selection_log "$log_path")
done

mkdir -p "$THETA_OUTPUT_DIR"
TRAIN_LOG="$THETA_OUTPUT_DIR/train_dp_scene_theta.log"
PID_FILE="$THETA_OUTPUT_DIR/train_dp_scene_theta.pid"
CMD_FILE="$THETA_OUTPUT_DIR/train_dp_scene_theta_command.txt"

CMD=(
  "$DP_PYTHON"
  "$CAMP_ROOT/scripts/integrations/train_diffusion_planner_theta.py"
  "${LOG_ARGS[@]}"
  --output_dir "$THETA_OUTPUT_DIR"
  --epochs "$EPOCHS"
  --lr "$LR"
  --l2_reg "$L2_REG"
  --val_fraction "$VAL_FRACTION"
  --feature_clip "$FEATURE_CLIP"
  --scale_percentile "$SCALE_PERCENTILE"
  --seed "$SEED"
  --label_source "$LABEL_SOURCE"
  --reward_key "$REWARD_KEY"
  --reward_progress_weight "$REWARD_PROGRESS_WEIGHT"
)

printf '%q ' "${CMD[@]}" > "$CMD_FILE"
printf '\n' >> "$CMD_FILE"

printf 'CAMP_ROOT=%s\n' "$CAMP_ROOT"
printf 'THETA_OUTPUT_DIR=%s\n' "$THETA_OUTPUT_DIR"
printf 'TRAIN_LOG=%s\n' "$TRAIN_LOG"
printf 'SELECTION_LOGS=%s\n' "$SELECTION_LOGS"

export PYTHONUNBUFFERED=1
if [[ "$BACKGROUND" == "1" ]]; then
  nohup "${CMD[@]}" > "$TRAIN_LOG" 2>&1 &
  printf '%s\n' "$!" > "$PID_FILE"
  printf 'started background training pid=%s\n' "$(cat "$PID_FILE")"
  printf 'monitor with: THETA_OUTPUT_DIR=%q bash %q\n' \
    "$THETA_OUTPUT_DIR" \
    "$CAMP_ROOT/scripts/integrations/monitor_diffusion_planner_theta.sh"
else
  "${CMD[@]}" 2>&1 | tee "$TRAIN_LOG"
fi
