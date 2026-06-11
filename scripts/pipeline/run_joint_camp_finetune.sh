#!/usr/bin/env bash
set -euo pipefail

# One-shot runner:
# 1) Train CAMP from the prebuilt cache.
# 2) Train Finetune-Safe from the same base checkpoint.
# 3) Evaluate CAMP, Finetune-Safe, and Finetune+CAMP-Select.

ROOT="${ROOT:-/root/autodl-tmp/camp_core}"
DATA_ROOT="${DATA_ROOT:-/root/autodl-tmp/dataset}"
CACHE_DIR="${CACHE_DIR:-/root/autodl-tmp/.unified_data_cache}"
MODEL_DIR="${MODEL_DIR:-$ROOT/adaptive-prediction/experiments/nuScenes/models/nusc_adaptive_tpp_scratch-01_Apr_2026_12_27_02}"
CONF_PATH="${CONF_PATH:-$MODEL_DIR/config.json}"
BASE_EPOCH="${BASE_EPOCH:-20}"

export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION="${PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION:-python}"
if ! [[ "${OMP_NUM_THREADS:-}" =~ ^[1-9][0-9]*$ ]]; then
  export OMP_NUM_THREADS=1
fi

CAMP_ITERS="${CAMP_ITERS:-100}"
CAMP_NUM_SCENARIOS="${CAMP_NUM_SCENARIOS:--1}"
FINETUNE_TRAIN_EPOCHS="${FINETUNE_TRAIN_EPOCHS:-120}"
FINETUNE_EVAL_EPOCHS="${FINETUNE_EVAL_EPOCHS:-60 90 120}"
NUM_CAND="${NUM_CAND:-12}"
RUN_TAG="${RUN_TAG:-mapaware_clearance_v2}"
LIVE_LOGS="${LIVE_LOGS:-1}"

ATOM_SCALES_PATH="${ATOM_SCALES_PATH:-$ROOT/models/production/atom_scales_${RUN_TAG}.json}"
TRAIN_CACHE_PATH="${TRAIN_CACHE_PATH:-$ROOT/data/cached_train_batch_${RUN_TAG}.pkl}"
EVAL_CACHE_PATH="${EVAL_CACHE_PATH:-$ROOT/data/cached_eval_batch_${RUN_TAG}.pkl}"
OFFLINE_WEIGHTS_PATH="${OFFLINE_WEIGHTS_PATH:-$ROOT/models/offline_weights.npy}"

CAMP_RISK_TYPE="${CAMP_RISK_TYPE:-cvar}"
CAMP_ALPHA="${CAMP_ALPHA:-0.9}"
CAMP_PRIOR_REG="${CAMP_PRIOR_REG:-1.0}"
CAMP_ANCHOR_WEIGHT="${CAMP_ANCHOR_WEIGHT:-0.0}"
MASTER_BATCH_SIZE="${MASTER_BATCH_SIZE:-${CAMP_MASTER_BATCH_SIZE:-500}}"
MAX_CUTS_PER_SCENE="${MAX_CUTS_PER_SCENE:-${CAMP_MAX_CUTS_PER_SCENE:-120}}"
CAMP_MODEL_PATH="${CAMP_OUTPUT_PATH:-$ROOT/models/camp_select_linear_it${CAMP_ITERS}_${RUN_TAG}.pt}"

FINETUNE_LOSS_MODE="${FINETUNE_LOSS_MODE:-camp_atoms}"
FINETUNE_RISK_TYPE="${FINETUNE_RISK_TYPE:-cvar}"
FINETUNE_CVAR_ALPHA="${FINETUNE_CVAR_ALPHA:-0.9}"
FINETUNE_WARMUP_EPOCHS="${FINETUNE_WARMUP_EPOCHS:-0}"
FINETUNE_RAMP_EPOCHS="${FINETUNE_RAMP_EPOCHS:-1}"
FINETUNE_SAFETY_RADIUS="${FINETUNE_SAFETY_RADIUS:-${SAFETY_RADIUS:-1.0}}"
FINETUNE_CLEARANCE_SOFT_MARGIN="${FINETUNE_CLEARANCE_SOFT_MARGIN:-${CLEARANCE_SOFT_MARGIN:-4.0}}"
FINETUNE_MAX_BATCHES_PER_EPOCH="${FINETUNE_MAX_BATCHES_PER_EPOCH:-0}"
EVAL_ATOM_CLIP="${EVAL_ATOM_CLIP:-10.0}"
FT_CHECKPOINT_PREFIX="${FT_CHECKPOINT_PREFIX:-finetuned_safe_${RUN_TAG}}"

CAMP_LOG="$ROOT/logs/camp_it${CAMP_ITERS}_${RUN_TAG}.log"
FT_LOG="$ROOT/logs/finetune_e${FINETUNE_TRAIN_EPOCHS}_${RUN_TAG}.log"
CAMP_TIMING_JSON="$ROOT/results/camp_train_timing_it${CAMP_ITERS}_${RUN_TAG}.json"
FT_TIMING_JSON="$ROOT/results/finetune_train_timing_e${FINETUNE_TRAIN_EPOCHS}_${RUN_TAG}.json"
TIME_COMPARE_JSON="$ROOT/results/training_time_compare_it${CAMP_ITERS}_e${FINETUNE_TRAIN_EPOCHS}_${RUN_TAG}.json"

export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
export PYTHONUNBUFFERED=1

mkdir -p "$ROOT/logs" "$ROOT/results" "$ROOT/models"

echo "=== Joint Run Config ==="
echo "ROOT=$ROOT"
echo "DATA_ROOT=$DATA_ROOT"
echo "CACHE_DIR=$CACHE_DIR"
echo "MODEL_DIR=$MODEL_DIR"
echo "CONF_PATH=$CONF_PATH"
echo "BASE_EPOCH=$BASE_EPOCH"
echo "CAMP_ITERS=$CAMP_ITERS"
echo "CAMP_NUM_SCENARIOS=$CAMP_NUM_SCENARIOS"
echo "FINETUNE_TRAIN_EPOCHS=$FINETUNE_TRAIN_EPOCHS"
echo "FINETUNE_EVAL_EPOCHS=$FINETUNE_EVAL_EPOCHS"
echo "NUM_CAND=$NUM_CAND"
echo "RUN_TAG=$RUN_TAG"
echo "FINETUNE_SAFETY_RADIUS=$FINETUNE_SAFETY_RADIUS"
echo "FINETUNE_CLEARANCE_SOFT_MARGIN=$FINETUNE_CLEARANCE_SOFT_MARGIN"
echo "FINETUNE_MAX_BATCHES_PER_EPOCH=$FINETUNE_MAX_BATCHES_PER_EPOCH"
echo "EVAL_ATOM_CLIP=$EVAL_ATOM_CLIP"
echo "ATOM_SCALES_PATH=$ATOM_SCALES_PATH"
echo "TRAIN_CACHE_PATH=$TRAIN_CACHE_PATH"
echo "EVAL_CACHE_PATH=$EVAL_CACHE_PATH"
echo "FT_CHECKPOINT_PREFIX=$FT_CHECKPOINT_PREFIX"
echo "LIVE_LOGS=$LIVE_LOGS"
echo "MASTER_BATCH_SIZE=$MASTER_BATCH_SIZE"
echo "MAX_CUTS_PER_SCENE=$MAX_CUTS_PER_SCENE"
echo "CAMP_MODEL_PATH=$CAMP_MODEL_PATH"
echo "CAMP_TIMING_JSON=$CAMP_TIMING_JSON"
echo "FT_TIMING_JSON=$FT_TIMING_JSON"
echo "TIME_COMPARE_JSON=$TIME_COMPARE_JSON"
echo "========================"

if [[ ! -f "$CONF_PATH" ]]; then
  echo "[Error] Config not found: $CONF_PATH" >&2
  exit 1
fi
if [[ ! -f "$TRAIN_CACHE_PATH" ]]; then
  echo "[Error] Train cache not found: $TRAIN_CACHE_PATH" >&2
  exit 1
fi
if [[ ! -f "$EVAL_CACHE_PATH" ]]; then
  echo "[Error] Eval cache not found: $EVAL_CACHE_PATH" >&2
  exit 1
fi
if [[ ! -f "$ATOM_SCALES_PATH" ]]; then
  echo "[Error] Atom scales not found: $ATOM_SCALES_PATH" >&2
  exit 1
fi

: > "$CAMP_LOG"
: > "$FT_LOG"

TAIL_CAMP_PID=""
TAIL_FT_PID=""

cleanup_tail() {
  if [[ -n "${TAIL_CAMP_PID:-}" ]]; then
    kill "$TAIL_CAMP_PID" 2>/dev/null || true
  fi
  if [[ -n "${TAIL_FT_PID:-}" ]]; then
    kill "$TAIL_FT_PID" 2>/dev/null || true
  fi
}
trap cleanup_tail EXIT

if [[ "$LIVE_LOGS" == "1" ]]; then
  echo "[Info] Streaming training logs live. Prefixes: [CAMP], [FT]"
  tail -n 0 -f "$CAMP_LOG" | sed -u 's/^/[CAMP] /' &
  TAIL_CAMP_PID=$!
  tail -n 0 -f "$FT_LOG" | sed -u 's/^/[FT] /' &
  TAIL_FT_PID=$!
fi

echo "[1/4] Launching CAMP (CPU) and Finetune (GPU/auto) in parallel..."
TRAIN_STAGE_START_TS=$(date +%s)
CAMP_START_TS=$(date +%s)

(
  cd "$ROOT"
  python -u scripts/train/train_camp_select.py \
    --cache_path "$TRAIN_CACHE_PATH" \
    --num_scenarios "$CAMP_NUM_SCENARIOS" \
    --device cpu \
    --output_path "$CAMP_MODEL_PATH" \
    --atom_scales_path "$ATOM_SCALES_PATH" \
    --risk_type "$CAMP_RISK_TYPE" \
    --alpha "$CAMP_ALPHA" \
    --prior_reg "$CAMP_PRIOR_REG" \
    --anchor_weight "$CAMP_ANCHOR_WEIGHT" \
    --offline_weights_path "$OFFLINE_WEIGHTS_PATH" \
    --solver CLARABEL \
    --master_batch_size "$MASTER_BATCH_SIZE" \
    --max_cuts_per_scene "$MAX_CUTS_PER_SCENE" \
    --max_iter "$CAMP_ITERS" \
    --timing_output_path "$CAMP_TIMING_JSON" \
    > "$CAMP_LOG" 2>&1
) &
CAMP_PID=$!

FT_START_TS=$(date +%s)
(
  cd "$ROOT/adaptive-prediction/experiments/nuScenes"
  FINETUNE_TIMING_OUTPUT_PATH="$FT_TIMING_JSON" python -u train_finetune_safe.py \
    --conf "$CONF_PATH" \
    --base_epoch "$BASE_EPOCH" \
    --train_data nusc_trainval-train \
    --trajdata_cache_dir "$CACHE_DIR" \
    --finetune_loss_mode "$FINETUNE_LOSS_MODE" \
    --finetune_risk_type "$FINETUNE_RISK_TYPE" \
    --finetune_cvar_alpha "$FINETUNE_CVAR_ALPHA" \
    --finetune_atom_scales_path "$ATOM_SCALES_PATH" \
    --finetune_checkpoint_prefix "$FT_CHECKPOINT_PREFIX" \
    --finetune_safety_radius "$FINETUNE_SAFETY_RADIUS" \
    --finetune_clearance_soft_margin "$FINETUNE_CLEARANCE_SOFT_MARGIN" \
    --finetune_max_batches_per_epoch "$FINETUNE_MAX_BATCHES_PER_EPOCH" \
    --finetune_warmup_epochs "$FINETUNE_WARMUP_EPOCHS" \
    --finetune_ramp_epochs "$FINETUNE_RAMP_EPOCHS" \
    --train_epochs "$FINETUNE_TRAIN_EPOCHS" \
    > "$FT_LOG" 2>&1
) &
FT_PID=$!

CAMP_STATUS=0
FT_STATUS=0
wait "$CAMP_PID" || CAMP_STATUS=$?
CAMP_END_TS=$(date +%s)
wait "$FT_PID" || FT_STATUS=$?
FT_END_TS=$(date +%s)
TRAIN_STAGE_END_TS=$(date +%s)
cleanup_tail

if [[ "$CAMP_STATUS" -ne 0 || "$FT_STATUS" -ne 0 ]]; then
  echo "[Error] Training failed. CAMP_STATUS=$CAMP_STATUS FT_STATUS=$FT_STATUS" >&2
  echo "  CAMP log: $CAMP_LOG" >&2
  echo "  FT log: $FT_LOG" >&2
  exit 1
fi

echo "[1/4] Training finished."
CAMP_TRAIN_S=$((CAMP_END_TS - CAMP_START_TS))
FT_TRAIN_S=$((FT_END_TS - FT_START_TS))
TRAIN_STAGE_S=$((TRAIN_STAGE_END_TS - TRAIN_STAGE_START_TS))

python - <<PY
import json
import os

camp_s = int("$CAMP_TRAIN_S")
ft_s = int("$FT_TRAIN_S")
stage_s = int("$TRAIN_STAGE_S")
camp_timing_path = r"$CAMP_TIMING_JSON"
ft_timing_path = r"$FT_TIMING_JSON"
output_path = r"$TIME_COMPARE_JSON"

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

camp_detail = load_json(camp_timing_path)
ft_detail = load_json(ft_timing_path)
payload = {
    "camp_train_wall_time_s": camp_s,
    "finetune_train_wall_time_s": ft_s,
    "parallel_train_stage_wall_time_s": stage_s,
    "camp_vs_finetune_ratio": (float(camp_s) / float(ft_s)) if ft_s > 0 else None,
    "camp_detail_timing_json": camp_timing_path if os.path.exists(camp_timing_path) else None,
    "finetune_detail_timing_json": ft_timing_path if os.path.exists(ft_timing_path) else None,
    "camp_reported_total_seconds": camp_detail.get("total_seconds", camp_detail.get("total_time_s")),
    "finetune_reported_total_seconds": ft_detail.get("total_seconds", ft_detail.get("total_time_s")),
    "run_tag": "$RUN_TAG",
    "base_epoch": int("$BASE_EPOCH"),
    "master_batch_size": int("$MASTER_BATCH_SIZE"),
    "max_cuts_per_scene": int("$MAX_CUTS_PER_SCENE"),
}

os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

ratio = payload["camp_vs_finetune_ratio"]
ratio_str = f"{ratio:.3f}x" if ratio is not None else "N/A"
print(f"[Time] CAMP train wall time: {camp_s/60:.2f} min")
print(f"[Time] Finetune train wall time: {ft_s/60:.2f} min")
print(f"[Time] CAMP / Finetune ratio: {ratio_str}")
print(f"[Time] Parallel train stage wall time: {stage_s/60:.2f} min")
print(f"[Time] Saved timing compare JSON: {output_path}")
PY

echo "[2/4] Evaluating CAMP..."
cd "$ROOT"
python scripts/eval/eval_camp_select.py \
  --cache_path "$EVAL_CACHE_PATH" \
  --model_path "$CAMP_MODEL_PATH" \
  --atom_scales_path "$ATOM_SCALES_PATH" \
  --atom_clip "$EVAL_ATOM_CLIP" \
  --output_path "$ROOT/results/camp_select_it${CAMP_ITERS}_${RUN_TAG}_preds.json"

python scripts/eval/unified_eval.py \
  --cache_path "$EVAL_CACHE_PATH" \
  --preds_path "$ROOT/results/camp_select_it${CAMP_ITERS}_${RUN_TAG}_preds.json" \
  --atom_scales_path "$ATOM_SCALES_PATH" \
  --atom_clip "$EVAL_ATOM_CLIP" \
  --output_path "$ROOT/results/camp_select_it${CAMP_ITERS}_${RUN_TAG}_metrics.json"

echo "[3/4] Evaluating Finetune-Safe and Finetune+CAMP-Select..."
for E in $FINETUNE_EVAL_EPOCHS; do
  FT_CKPT="$MODEL_DIR/${FT_CHECKPOINT_PREFIX}_${E}.pt"
  if [[ ! -f "$FT_CKPT" ]]; then
    echo "  [Skip] Missing checkpoint: $FT_CKPT"
    continue
  fi

  python scripts/eval/eval_finetune.py \
    --data_root "$DATA_ROOT" \
    --cache_dir "$CACHE_DIR" \
    --traj_conf_path "$CONF_PATH" \
    --traj_model_dir "$MODEL_DIR" \
    --base_epoch "$BASE_EPOCH" \
    --finetuned_epoch "$E" \
    --finetuned_prefix "$FT_CHECKPOINT_PREFIX" \
    --atom_scales_path "$ATOM_SCALES_PATH" \
    --atom_clip "$EVAL_ATOM_CLIP" \
    --split nusc_trainval-val \
    --output_path "$ROOT/results/finetune_safe_e${E}_${RUN_TAG}_metrics.json"

  python scripts/eval/eval_finetune_camp_select.py \
    --data_root "$DATA_ROOT" \
    --cache_dir "$CACHE_DIR" \
    --traj_conf_path "$CONF_PATH" \
    --traj_model_dir "$MODEL_DIR" \
    --base_epoch "$BASE_EPOCH" \
    --finetuned_epoch "$E" \
    --finetuned_prefix "$FT_CHECKPOINT_PREFIX" \
    --camp_model_path "$CAMP_MODEL_PATH" \
    --embed_conf_path "$CONF_PATH" \
    --embed_model_dir "$MODEL_DIR" \
    --embed_base_epoch "$BASE_EPOCH" \
    --atom_scales_path "$ATOM_SCALES_PATH" \
    --atom_clip "$EVAL_ATOM_CLIP" \
    --num_candidates "$NUM_CAND" \
    --split nusc_trainval-val \
    --output_metrics_path "$ROOT/results/finetune_camp_select_e${E}_${RUN_TAG}_metrics.json" \
    --output_preds_path "$ROOT/results/finetune_camp_select_e${E}_${RUN_TAG}_preds.json"
done

echo "[4/4] Printing final table..."
JOINT_METRIC_FILES=("$ROOT/results/camp_select_it${CAMP_ITERS}_${RUN_TAG}_metrics.json")
for E in $FINETUNE_EVAL_EPOCHS; do
  for METRIC_PATH in \
    "$ROOT/results/finetune_safe_e${E}_${RUN_TAG}_metrics.json" \
    "$ROOT/results/finetune_camp_select_e${E}_${RUN_TAG}_metrics.json"; do
    if [[ -f "$METRIC_PATH" ]]; then
      JOINT_METRIC_FILES+=("$METRIC_PATH")
    fi
  done
done
TIMING_ARGS=()
if [[ -f "$TIME_COMPARE_JSON" ]]; then
  TIMING_ARGS=(--timing_compare_files "$TIME_COMPARE_JSON")
fi
python scripts/eval/print_table.py --results_dir "$ROOT/results" --metric_files "${JOINT_METRIC_FILES[@]}" "${TIMING_ARGS[@]}"

echo "Done. Logs:"
echo "  $CAMP_LOG"
echo "  $FT_LOG"
