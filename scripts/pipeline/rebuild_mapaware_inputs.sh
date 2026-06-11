#!/usr/bin/env bash
set -euo pipefail

# Rebuild the map-aware inputs used by the joint CAMP/finetune run:
# 1) atom scales
# 2) training cache
# 3) evaluation cache
#
# Optional env overrides:
#   ROOT=/root/autodl-tmp/camp_core
#   DATA_ROOT=/root/autodl-tmp/dataset
#   CACHE_DIR=/root/autodl-tmp/.unified_data_cache
#   MODEL_DIR=$ROOT/adaptive-prediction/experiments/nuScenes/models/...
#   BASE_EPOCH=20
#   RUN_TAG=mapaware
#   NUM_SCALE_SAMPLES=4000
#   NUM_CAND=12
#   NUM_TRAIN_SCENARIOS=-1
#   NUM_EVAL_SCENARIOS=-1
#   REBUILD_TRAJDATA_CACHE=0

ROOT="${ROOT:-/root/autodl-tmp/camp_core}"
DATA_ROOT="${DATA_ROOT:-/root/autodl-tmp/dataset}"
CACHE_DIR="${CACHE_DIR:-/root/autodl-tmp/.unified_data_cache}"
MODEL_DIR="${MODEL_DIR:-$ROOT/adaptive-prediction/experiments/nuScenes/models/nusc_adaptive_tpp_scratch-01_Apr_2026_12_27_02}"
BASE_EPOCH="${BASE_EPOCH:-20}"
RUN_TAG="${RUN_TAG:-mapaware}"
NUM_SCALE_SAMPLES="${NUM_SCALE_SAMPLES:-4000}"
NUM_CAND="${NUM_CAND:-12}"
NUM_TRAIN_SCENARIOS="${NUM_TRAIN_SCENARIOS:--1}"
NUM_EVAL_SCENARIOS="${NUM_EVAL_SCENARIOS:--1}"
NUM_WORKERS="${NUM_WORKERS:-0}"
BATCH_SIZE="${BATCH_SIZE:-4}"
REBUILD_TRAJDATA_CACHE="${REBUILD_TRAJDATA_CACHE:-0}"

CONF_PATH="$MODEL_DIR/config.json"
ATOM_SCALES_PATH="${ATOM_SCALES_PATH:-$ROOT/models/production/atom_scales_${RUN_TAG}.json}"
TRAIN_CACHE_PATH="${TRAIN_CACHE_PATH:-$ROOT/data/cached_train_batch_${RUN_TAG}.pkl}"
EVAL_CACHE_PATH="${EVAL_CACHE_PATH:-$ROOT/data/cached_eval_batch_${RUN_TAG}.pkl}"

export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
export PYTHONUNBUFFERED=1

mkdir -p "$ROOT/models/production" "$ROOT/data" "$ROOT/logs"

echo "=== Map-Aware Rebuild Config ==="
echo "ROOT=$ROOT"
echo "DATA_ROOT=$DATA_ROOT"
echo "CACHE_DIR=$CACHE_DIR"
echo "MODEL_DIR=$MODEL_DIR"
echo "BASE_EPOCH=$BASE_EPOCH"
echo "RUN_TAG=$RUN_TAG"
echo "ATOM_SCALES_PATH=$ATOM_SCALES_PATH"
echo "TRAIN_CACHE_PATH=$TRAIN_CACHE_PATH"
echo "EVAL_CACHE_PATH=$EVAL_CACHE_PATH"
echo "NUM_SCALE_SAMPLES=$NUM_SCALE_SAMPLES"
echo "NUM_CAND=$NUM_CAND"
echo "NUM_TRAIN_SCENARIOS=$NUM_TRAIN_SCENARIOS"
echo "NUM_EVAL_SCENARIOS=$NUM_EVAL_SCENARIOS"
echo "REBUILD_TRAJDATA_CACHE=$REBUILD_TRAJDATA_CACHE"
echo "==============================="

if [ ! -f "$CONF_PATH" ]; then
  echo "[Error] Config not found: $CONF_PATH"
  exit 1
fi

cd "$ROOT"

REBUILD_CACHE_ARGS=()
if [ "$REBUILD_TRAJDATA_CACHE" = "1" ]; then
  REBUILD_CACHE_ARGS+=(--rebuild_trajdata_cache)
fi

echo "[1/3] Computing map-aware atom scales..."
python -u scripts/tools/compute_atom_scales.py \
  --data_root "$DATA_ROOT" \
  --cache_dir "$CACHE_DIR" \
  --output_file "$ATOM_SCALES_PATH" \
  --num_samples "$NUM_SCALE_SAMPLES" \
  --num_candidates "$NUM_CAND" \
  --num_workers "$NUM_WORKERS" \
  --trajectron_conf "$CONF_PATH" \
  --trajectron_model_dir "$MODEL_DIR" \
  --trajectron_epoch "$BASE_EPOCH" \
  "${REBUILD_CACHE_ARGS[@]}"

echo "[2/3] Building map-aware train cache..."
python -u scripts/data_gen/cache_dataset.py \
  --data_root "$DATA_ROOT" \
  --cache_dir "$CACHE_DIR" \
  --batch_size "$BATCH_SIZE" \
  --num_workers "$NUM_WORKERS" \
  --num_scenarios "$NUM_TRAIN_SCENARIOS" \
  --num_candidates "$NUM_CAND" \
  --output_path "$TRAIN_CACHE_PATH" \
  --trajectron_conf "$CONF_PATH" \
  --trajectron_model_dir "$MODEL_DIR" \
  --trajectron_epoch "$BASE_EPOCH" \
  --split nusc_trainval-train \
  "${REBUILD_CACHE_ARGS[@]}"

echo "[3/3] Building map-aware eval cache..."
python -u scripts/data_gen/cache_dataset.py \
  --data_root "$DATA_ROOT" \
  --cache_dir "$CACHE_DIR" \
  --batch_size "$BATCH_SIZE" \
  --num_workers "$NUM_WORKERS" \
  --num_scenarios "$NUM_EVAL_SCENARIOS" \
  --num_candidates "$NUM_CAND" \
  --output_path "$EVAL_CACHE_PATH" \
  --trajectron_conf "$CONF_PATH" \
  --trajectron_model_dir "$MODEL_DIR" \
  --trajectron_epoch "$BASE_EPOCH" \
  --split nusc_trainval-val \
  "${REBUILD_CACHE_ARGS[@]}"

echo "Done. Check the printed Map source counts; vector_map should dominate."
