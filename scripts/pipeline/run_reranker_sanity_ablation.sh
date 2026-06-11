#!/usr/bin/env bash
set -Eeuo pipefail

export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION="${PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION:-python}"

ROOT="${ROOT:-/root/autodl-tmp/camp_core}"
DATA_ROOT="${DATA_ROOT:-/root/autodl-tmp/dataset}"
CACHE_DIR="${CACHE_DIR:-/root/autodl-tmp/.unified_data_cache}"
RUN_TAG="${RUN_TAG:-mapaware_clearance_v2_cvxpy_full_ft20_k50}"
MODEL_DIR="${MODEL_DIR:-$ROOT/adaptive-prediction/experiments/nuScenes/models/nusc_adaptive_tpp_scratch-01_Apr_2026_12_27_02}"
CONF_PATH="${CONF_PATH:-$MODEL_DIR/config.json}"
BASE_EPOCH="${BASE_EPOCH:-20}"

ATOM_SCALES_PATH="${ATOM_SCALES_PATH:-$ROOT/models/production/atom_scales_${RUN_TAG}.json}"
TRAIN_CACHE_PATH="${TRAIN_CACHE_PATH:-$ROOT/data/cached_train_batch_${RUN_TAG}.pkl}"
EVAL_CACHE_PATH="${EVAL_CACHE_PATH:-$ROOT/data/cached_eval_batch_${RUN_TAG}.pkl}"

RESULTS_DIR="${RESULTS_DIR:-$ROOT/results}"
LOG_DIR="${LOG_DIR:-$ROOT/logs/reranker_sanity_${RUN_TAG}}"
MODEL_OUT_DIR="${MODEL_OUT_DIR:-$ROOT/models/reranker_sanity_${RUN_TAG}}"

SEED="${SEED:-42}"
RERANKER_SANITY_EPOCHS="${RERANKER_SANITY_EPOCHS:-3}"
RERANKER_SANITY_NUM_SCENARIOS="${RERANKER_SANITY_NUM_SCENARIOS:-50000}"
RERANKER_TRAIN_BATCH_SIZE="${RERANKER_TRAIN_BATCH_SIZE:-256}"
RERANKER_LR="${RERANKER_LR:-0.001}"
RERANKER_SAFETY_TEMP="${RERANKER_SAFETY_TEMP:-1.0}"
EVAL_ATOM_CLIP="${EVAL_ATOM_CLIP:-10.0}"
EVAL_DEVICE="${EVAL_DEVICE:-cuda}"

mkdir -p "$RESULTS_DIR" "$LOG_DIR" "$MODEL_OUT_DIR"

echo "=== Reranker Sanity Ablation ==="
echo "RUN_TAG=$RUN_TAG"
echo "TRAIN_CACHE_PATH=$TRAIN_CACHE_PATH"
echo "EVAL_CACHE_PATH=$EVAL_CACHE_PATH"
echo "ATOM_SCALES_PATH=$ATOM_SCALES_PATH"
echo "SEED=$SEED"
echo "RERANKER_SANITY_EPOCHS=$RERANKER_SANITY_EPOCHS"
echo "RERANKER_SANITY_NUM_SCENARIOS=$RERANKER_SANITY_NUM_SCENARIOS"
echo "================================="

run_variant() {
  local label="$1"
  local lambda_safe="$2"
  local model_path="$MODEL_OUT_DIR/reranker_${label}.pt"
  local preds_path="$RESULTS_DIR/reranker_sanity_${label}_${RUN_TAG}_preds.json"
  local metrics_path="$RESULTS_DIR/reranker_sanity_${label}_${RUN_TAG}_metrics.json"
  local train_log="$LOG_DIR/train_${label}.log"
  local eval_log="$LOG_DIR/eval_${label}.log"
  local metrics_log="$LOG_DIR/metrics_${label}.log"

  echo
  echo "===== Training reranker sanity variant: $label (lambda_safe=$lambda_safe) ====="
  python -u scripts/train/train_reranker.py \
    --data_root "$DATA_ROOT" \
    --cache_dir "$CACHE_DIR" \
    --trajectron_conf "$CONF_PATH" \
    --trajectron_model_dir "$MODEL_DIR" \
    --trajectron_epoch "$BASE_EPOCH" \
    --num_scenarios "$RERANKER_SANITY_NUM_SCENARIOS" \
    --cache_path "$TRAIN_CACHE_PATH" \
    --epochs "$RERANKER_SANITY_EPOCHS" \
    --lr "$RERANKER_LR" \
    --train_batch_size "$RERANKER_TRAIN_BATCH_SIZE" \
    --lambda_safe "$lambda_safe" \
    --safety_temp "$RERANKER_SAFETY_TEMP" \
    --seed "$SEED" \
    --atom_scales_path "$ATOM_SCALES_PATH" \
    --output_path "$model_path" \
    2>&1 | tee "$train_log"

  echo
  echo "===== Evaluating reranker sanity variant: $label ====="
  python -u scripts/eval/eval_reranker.py \
    --cache_path "$EVAL_CACHE_PATH" \
    --model_path "$model_path" \
    --atom_scales_path "$ATOM_SCALES_PATH" \
    --atom_clip "$EVAL_ATOM_CLIP" \
    --device "$EVAL_DEVICE" \
    --output_path "$preds_path" \
    2>&1 | tee "$eval_log"

  python -u scripts/eval/unified_eval.py \
    --cache_path "$EVAL_CACHE_PATH" \
    --preds_path "$preds_path" \
    --atom_scales_path "$ATOM_SCALES_PATH" \
    --output_path "$metrics_path" \
    2>&1 | tee "$metrics_log"
}

run_variant "lambda0" "0.0"
run_variant "lambda0p1" "0.1"

python - "$RESULTS_DIR/reranker_sanity_lambda0_${RUN_TAG}_metrics.json" \
          "$RESULTS_DIR/reranker_sanity_lambda0p1_${RUN_TAG}_metrics.json" <<'PY'
import json
import os
import sys

rows = []
for label, path in zip(["lambda_safe=0.0", "lambda_safe=0.1"], sys.argv[1:]):
    with open(path, "r") as f:
        m = json.load(f)
    rows.append((label, m))

print("\n### Reranker Sanity Ablation")
print("| Variant | ADE | FDE | Violation | RMS Accel | RMS Jerk | Safety CVaR |")
print("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
for label, m in rows:
    print(
        f"| **{label}** | {m['Mean_ADE']:.2f} | {m['Mean_FDE']:.2f} | "
        f"{100.0 * m['Violation_Rate']:.1f}% | {m['RMS_Accel']:.2f} | "
        f"{m['RMS_Jerk']:.2f} | {m['CVaR_0.90_Safety']:.2f} |"
    )

print("\nMetric files:")
for path in sys.argv[1:]:
    print(f"  {path}")
PY

echo
echo "Done. Logs: $LOG_DIR"
