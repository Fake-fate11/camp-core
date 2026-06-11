#!/usr/bin/env bash
set -Eeuo pipefail

# Full Table-2 rebuild for the map-aware + dynamic-clearance experiment.
# It cleans reproducible artifacts, rebuilds atom/cache inputs, retrains every
# learned row in Table 2, then regenerates predictions/metrics from one eval cache.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

ROOT="${ROOT:-$DEFAULT_ROOT}"
DATA_ROOT="${DATA_ROOT:-/root/autodl-tmp/dataset}"
CACHE_DIR="${CACHE_DIR:-/root/autodl-tmp/.unified_data_cache}"
MODEL_DIR="${MODEL_DIR:-$ROOT/adaptive-prediction/experiments/nuScenes/models/nusc_adaptive_tpp_scratch-01_Apr_2026_12_27_02}"
BASE_EPOCH="${BASE_EPOCH:-20}"
RUN_TAG="${RUN_TAG:-mapaware_clearance_v2}"
CONF_PATH="${CONF_PATH:-$MODEL_DIR/config.json}"
DEVICE="${DEVICE:-cuda}"

export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION="${PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION:-python}"
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"
if ! [[ "${OMP_NUM_THREADS:-}" =~ ^[1-9][0-9]*$ ]]; then
  export OMP_NUM_THREADS=1
fi

# Stage switches. Set any to 0 to resume from a later step.
DO_CLEAN="${DO_CLEAN:-1}"
RESET_TRAJDATA_CACHE="${RESET_TRAJDATA_CACHE:-1}"
DO_REBUILD_INPUTS="${DO_REBUILD_INPUTS:-1}"
DO_SANITY="${DO_SANITY:-1}"
DO_STATIC="${DO_STATIC:-1}"
DO_RERANKER="${DO_RERANKER:-1}"
DO_CAMP_FINETUNE="${DO_CAMP_FINETUNE:-1}"
DO_CAMP_PREDS="${DO_CAMP_PREDS:-0}"
DO_FINETUNE_EVALS="${DO_FINETUNE_EVALS:-0}"
DO_BASELINE_PREDS="${DO_BASELINE_PREDS:-1}"
DO_RERANKER_PREDS="${DO_RERANKER_PREDS:-1}"
DO_METRICS="${DO_METRICS:-1}"

# Rebuild scale/cache knobs.
REBUILD_TRAJDATA_CACHE="${REBUILD_TRAJDATA_CACHE:-1}"
NUM_SCALE_SAMPLES="${NUM_SCALE_SAMPLES:-20000}"
NUM_TRAIN_SCENARIOS="${NUM_TRAIN_SCENARIOS:--1}"
NUM_EVAL_SCENARIOS="${NUM_EVAL_SCENARIOS:--1}"
NUM_WORKERS="${NUM_WORKERS:-0}"
SANITY_SAMPLES="${SANITY_SAMPLES:-500}"

# Learned trainer scenario counts support -1 for all available training scenarios.
LEARNED_NUM_SCENARIOS="${LEARNED_NUM_SCENARIOS:-20000}"
STATIC_NUM_SCENARIOS="${STATIC_NUM_SCENARIOS:-$LEARNED_NUM_SCENARIOS}"
RERANKER_NUM_SCENARIOS="${RERANKER_NUM_SCENARIOS:-$LEARNED_NUM_SCENARIOS}"
CAMP_NUM_SCENARIOS="${CAMP_NUM_SCENARIOS:-$LEARNED_NUM_SCENARIOS}"

STATIC_EPOCHS="${STATIC_EPOCHS:-200}"
STATIC_LR="${STATIC_LR:-0.01}"
STATIC_L1_REG="${STATIC_L1_REG:-0.01}"
STATIC_NUM_CANDIDATES="${STATIC_NUM_CANDIDATES:-10}"

RERANKER_EPOCHS="${RERANKER_EPOCHS:-10}"
RERANKER_LR="${RERANKER_LR:-0.001}"
RERANKER_TRAIN_BATCH_SIZE="${RERANKER_TRAIN_BATCH_SIZE:-256}"
RERANKER_LAMBDA_SAFE="${RERANKER_LAMBDA_SAFE:-0.1}"
RERANKER_SAFETY_TEMP="${RERANKER_SAFETY_TEMP:-1.0}"

CAMP_ITERS="${CAMP_ITERS:-100}"
NUM_CAND="${NUM_CAND:-12}"
CAMP_PRIOR_REG="${CAMP_PRIOR_REG:-1.0}"
CAMP_ANCHOR_WEIGHT="${CAMP_ANCHOR_WEIGHT:-0.0}"
CAMP_RISK_TYPE="${CAMP_RISK_TYPE:-cvar}"
CAMP_ALPHA="${CAMP_ALPHA:-0.9}"
CAMP_MASTER_BATCH_SIZE="${CAMP_MASTER_BATCH_SIZE:-500}"
CAMP_MAX_CUTS_PER_SCENE="${CAMP_MAX_CUTS_PER_SCENE:-${MAX_CUTS_PER_SCENE:-120}}"

FINETUNE_TRAIN_EPOCHS="${FINETUNE_TRAIN_EPOCHS:-120}"
FINETUNE_EVAL_EPOCHS="${FINETUNE_EVAL_EPOCHS:-60 90 120}"
FT_CHECKPOINT_PREFIX="${FT_CHECKPOINT_PREFIX:-finetuned_safe_${RUN_TAG}}"
FINETUNE_LOSS_MODE="${FINETUNE_LOSS_MODE:-camp_atoms}"
FINETUNE_RISK_TYPE="${FINETUNE_RISK_TYPE:-cvar}"
FINETUNE_CVAR_ALPHA="${FINETUNE_CVAR_ALPHA:-0.9}"
FINETUNE_WARMUP_EPOCHS="${FINETUNE_WARMUP_EPOCHS:-0}"
FINETUNE_RAMP_EPOCHS="${FINETUNE_RAMP_EPOCHS:-1}"
FINETUNE_MAX_BATCHES_PER_EPOCH="${FINETUNE_MAX_BATCHES_PER_EPOCH:-0}"
SAFETY_RADIUS="${SAFETY_RADIUS:-1.0}"
CLEARANCE_SOFT_MARGIN="${CLEARANCE_SOFT_MARGIN:-4.0}"
EVAL_ATOM_CLIP="${EVAL_ATOM_CLIP:-10.0}"

ATOM_SCALES_PATH="${ATOM_SCALES_PATH:-$ROOT/models/production/atom_scales_${RUN_TAG}.json}"
TRAIN_CACHE_PATH="${TRAIN_CACHE_PATH:-$ROOT/data/cached_train_batch_${RUN_TAG}.pkl}"
EVAL_CACHE_PATH="${EVAL_CACHE_PATH:-$ROOT/data/cached_eval_batch_${RUN_TAG}.pkl}"
CANON_ATOM_SCALES_PATH="$ROOT/models/production/atom_scales.json"
CANON_TRAIN_CACHE_PATH="$ROOT/data/cached_train_batch.pkl"
CANON_EVAL_CACHE_PATH="$ROOT/data/cached_eval_batch.pkl"

RUN_MODEL_DIR="$ROOT/models/$RUN_TAG"
OFFLINE_WEIGHTS_PATH="$RUN_MODEL_DIR/offline_weights.npy"
RERANKER_SAFE_PATH="$RUN_MODEL_DIR/reranker_safe.pt"
CAMP_SELECT_PATH="$RUN_MODEL_DIR/camp_select_it${CAMP_ITERS}.pt"
CANON_CAMP_SELECT_PATH="$ROOT/models/camp_select_linear.pt"
CAMP_OUTPUT_PATH="${CAMP_OUTPUT_PATH:-$CANON_CAMP_SELECT_PATH}"
RESULTS_DIR="$ROOT/results"
LOG_DIR="$ROOT/logs/table2_${RUN_TAG}"
TIME_COMPARE_JSON="$RESULTS_DIR/training_time_compare_it${CAMP_ITERS}_e${FINETUNE_TRAIN_EPOCHS}_${RUN_TAG}.json"

die() {
  echo "[ERROR] $*" >&2
  exit 1
}

need_positive_count() {
  local name="$1"
  local value="$2"
  if [[ ! "$value" =~ ^[0-9]+$ ]] || [[ "$value" -le 0 ]]; then
    die "$name must be a positive integer for legacy learned trainers; got '$value'."
  fi
}

need_positive_count_or_all() {
  local name="$1"
  local value="$2"
  if [[ "$value" == "-1" ]]; then
    return 0
  fi
  if [[ ! "$value" =~ ^[0-9]+$ ]] || [[ "$value" -le 0 ]]; then
    die "$name must be -1 for all cached scenarios or a positive integer; got '$value'."
  fi
}

run_logged() {
  local name="$1"
  shift
  mkdir -p "$LOG_DIR"
  echo
  echo "===== [$name] $(date '+%F %T') ====="
  "$@" 2>&1 | tee "$LOG_DIR/${name}.log"
}

link_or_copy() {
  local src="$1"
  local dst="$2"
  [[ -e "$src" ]] || die "Missing source artifact: $src"
  if [[ "$(realpath -m "$src")" == "$(realpath -m "$dst")" ]]; then
    return 0
  fi
  mkdir -p "$(dirname "$dst")"
  rm -f "$dst"
  if ln -s "$src" "$dst" 2>/dev/null; then
    return 0
  fi
  cp -f "$src" "$dst"
}

safe_rm_rf() {
  local target="$1"
  local root_real
  local target_real
  root_real="$(realpath -m "$ROOT")"
  target_real="$(realpath -m "$target")"
  [[ "$target_real" == "$root_real"/* ]] || die "Refusing to delete outside ROOT: $target"
  [[ "$target_real" != "$root_real" ]] || die "Refusing to delete ROOT itself"
  rm -rf "$target_real"
}

clean_artifacts() {
  echo "[Clean] Removing reproducible Table-2 artifacts under $ROOT"
  mkdir -p "$ROOT/models/production" "$ROOT/data" "$ROOT/models" "$ROOT/results"

  find "$ROOT/models/production" -maxdepth 1 \( -type f -o -type l \) \
    -name "atom_scales*.json" -delete

  find "$ROOT/data" -maxdepth 1 \( -type f -o -type l \) \( \
    -name "cached_*batch*.pkl" -o \
    -name "training_data*.pkl" \
  \) -delete

  find "$ROOT/models" -maxdepth 1 \( -type f -o -type l \) \( \
    -name "camp_select*.pt" -o \
    -name "reranker*.pt" -o \
    -name "reranker_train_data*.pt" -o \
    -name "offline_weights*.npy" \
  \) -delete

  find "$ROOT/results" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
  safe_rm_rf "$RUN_MODEL_DIR"

  if [[ -d "$ROOT/logs" ]]; then
    find "$ROOT/logs" -mindepth 1 -maxdepth 1 -name "table2_*" -exec rm -rf {} +
  fi

  # Keep the base model directory, but remove finetune outputs created inside it.
  if [[ -d "$MODEL_DIR" ]]; then
    find "$MODEL_DIR" -maxdepth 1 \( -type f -o -type l \) \( \
      -name "*finetune*.pt" -o \
      -name "*camp_atoms*.pt" -o \
      -name "*safe*.pt" \
    \) -delete
  fi

  if [[ "$RESET_TRAJDATA_CACHE" == "1" ]]; then
    local cache_real
    local root_real
    cache_real="$(realpath -m "$CACHE_DIR")"
    root_real="$(realpath -m "$ROOT")"
    if [[ "$cache_real" != "/root/autodl-tmp/.unified_data_cache" && \
          "$cache_real" != "$root_real/.unified_data_cache" ]]; then
      die "Refusing to reset unexpected CACHE_DIR: $CACHE_DIR"
    fi
    rm -rf "$cache_real"
    mkdir -p "$cache_real"
  fi
}

sync_canonical_artifacts() {
  link_or_copy "$ATOM_SCALES_PATH" "$CANON_ATOM_SCALES_PATH"
  link_or_copy "$TRAIN_CACHE_PATH" "$CANON_TRAIN_CACHE_PATH"
  link_or_copy "$EVAL_CACHE_PATH" "$CANON_EVAL_CACHE_PATH"
}

eval_reranker_preds() {
  local out_path="$RESULTS_DIR/reranker_safe_preds.json"
  if python -u scripts/eval/eval_reranker.py \
      --cache_path "$EVAL_CACHE_PATH" \
      --model_path "$RERANKER_SAFE_PATH" \
      --atom_scales_path "$ATOM_SCALES_PATH" \
      --atom_clip "$EVAL_ATOM_CLIP" \
      --output_path "$out_path" \
      --device "$DEVICE"; then
    return 0
  fi

  echo "[Eval] Retrying reranker eval with --reranker_path."
  python -u scripts/eval/eval_reranker.py \
    --cache_path "$EVAL_CACHE_PATH" \
    --reranker_path "$RERANKER_SAFE_PATH" \
    --atom_scales_path "$ATOM_SCALES_PATH" \
    --atom_clip "$EVAL_ATOM_CLIP" \
    --output_path "$out_path" \
    --device "$DEVICE"
}

eval_camp_preds() {
  local camp_model_for_eval="$CAMP_OUTPUT_PATH"
  if [[ ! -f "$camp_model_for_eval" && -f "$CAMP_SELECT_PATH" ]]; then
    camp_model_for_eval="$CAMP_SELECT_PATH"
  fi
  [[ -f "$camp_model_for_eval" ]] || die "CAMP checkpoint not found for CAMP eval: $CAMP_OUTPUT_PATH or $CAMP_SELECT_PATH"

  python scripts/eval/eval_camp_select.py \
    --cache_path "$EVAL_CACHE_PATH" \
    --model_path "$camp_model_for_eval" \
    --atom_scales_path "$ATOM_SCALES_PATH" \
    --atom_clip "$EVAL_ATOM_CLIP" \
    --output_path "$RESULTS_DIR/camp_select_it${CAMP_ITERS}_${RUN_TAG}_preds.json"
}

eval_finetune_rows() {
  local E
  local ft_ckpt
  local camp_model_for_eval="$CAMP_OUTPUT_PATH"
  if [[ ! -f "$camp_model_for_eval" && -f "$CAMP_SELECT_PATH" ]]; then
    camp_model_for_eval="$CAMP_SELECT_PATH"
  fi
  [[ -f "$camp_model_for_eval" ]] || die "CAMP checkpoint not found for Finetune+CAMP eval: $CAMP_OUTPUT_PATH or $CAMP_SELECT_PATH"

  for E in $FINETUNE_EVAL_EPOCHS; do
    ft_ckpt="$MODEL_DIR/${FT_CHECKPOINT_PREFIX}_${E}.pt"
    if [[ ! -f "$ft_ckpt" ]]; then
      echo "  [Skip] Missing checkpoint: $ft_ckpt"
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
      --output_path "$RESULTS_DIR/finetune_safe_e${E}_${RUN_TAG}_metrics.json"

    python scripts/eval/eval_finetune_camp_select.py \
      --data_root "$DATA_ROOT" \
      --cache_dir "$CACHE_DIR" \
      --traj_conf_path "$CONF_PATH" \
      --traj_model_dir "$MODEL_DIR" \
      --base_epoch "$BASE_EPOCH" \
      --finetuned_epoch "$E" \
      --finetuned_prefix "$FT_CHECKPOINT_PREFIX" \
      --camp_model_path "$camp_model_for_eval" \
      --embed_conf_path "$CONF_PATH" \
      --embed_model_dir "$MODEL_DIR" \
      --embed_base_epoch "$BASE_EPOCH" \
      --atom_scales_path "$ATOM_SCALES_PATH" \
      --atom_clip "$EVAL_ATOM_CLIP" \
      --num_candidates "$NUM_CAND" \
      --split nusc_trainval-val \
      --output_metrics_path "$RESULTS_DIR/finetune_camp_select_e${E}_${RUN_TAG}_metrics.json" \
      --output_preds_path "$RESULTS_DIR/finetune_camp_select_e${E}_${RUN_TAG}_preds.json"
  done
}

print_config() {
  cat <<EOF
=== Table-2 Map-Aware Clearance Pipeline ===
ROOT=$ROOT
DATA_ROOT=$DATA_ROOT
CACHE_DIR=$CACHE_DIR
MODEL_DIR=$MODEL_DIR
CONF_PATH=$CONF_PATH
BASE_EPOCH=$BASE_EPOCH
RUN_TAG=$RUN_TAG
ATOM_SCALES_PATH=$ATOM_SCALES_PATH
TRAIN_CACHE_PATH=$TRAIN_CACHE_PATH
EVAL_CACHE_PATH=$EVAL_CACHE_PATH
LEARNED_NUM_SCENARIOS=$LEARNED_NUM_SCENARIOS
CAMP_ITERS=$CAMP_ITERS
NUM_CAND=$NUM_CAND
CAMP_MASTER_BATCH_SIZE=$CAMP_MASTER_BATCH_SIZE
CAMP_MAX_CUTS_PER_SCENE=$CAMP_MAX_CUTS_PER_SCENE
FINETUNE_TRAIN_EPOCHS=$FINETUNE_TRAIN_EPOCHS
FINETUNE_EVAL_EPOCHS=$FINETUNE_EVAL_EPOCHS
FT_CHECKPOINT_PREFIX=$FT_CHECKPOINT_PREFIX
FINETUNE_MAX_BATCHES_PER_EPOCH=$FINETUNE_MAX_BATCHES_PER_EPOCH
DO_CAMP_PREDS=$DO_CAMP_PREDS
DO_FINETUNE_EVALS=$DO_FINETUNE_EVALS
EVAL_ATOM_CLIP=$EVAL_ATOM_CLIP
RESULTS_DIR=$RESULTS_DIR
LOG_DIR=$LOG_DIR
TIME_COMPARE_JSON=$TIME_COMPARE_JSON
============================================
EOF
}

main() {
  cd "$ROOT"
  [[ -d "$DATA_ROOT" ]] || die "DATA_ROOT not found: $DATA_ROOT"
  [[ -d "$MODEL_DIR" ]] || die "MODEL_DIR not found: $MODEL_DIR"
  [[ -f "$CONF_PATH" ]] || die "CONF_PATH not found: $CONF_PATH"

  need_positive_count_or_all STATIC_NUM_SCENARIOS "$STATIC_NUM_SCENARIOS"
  need_positive_count_or_all RERANKER_NUM_SCENARIOS "$RERANKER_NUM_SCENARIOS"
  need_positive_count_or_all CAMP_NUM_SCENARIOS "$CAMP_NUM_SCENARIOS"

  print_config

  if [[ "$DO_CLEAN" == "1" ]]; then
    clean_artifacts
  fi

  mkdir -p "$RUN_MODEL_DIR" "$RESULTS_DIR" "$LOG_DIR" "$ROOT/models/production" "$ROOT/data"

  if [[ "$DO_REBUILD_INPUTS" == "1" ]]; then
    run_logged 01_rebuild_inputs env \
      ROOT="$ROOT" \
      DATA_ROOT="$DATA_ROOT" \
      CACHE_DIR="$CACHE_DIR" \
      MODEL_DIR="$MODEL_DIR" \
      BASE_EPOCH="$BASE_EPOCH" \
      RUN_TAG="$RUN_TAG" \
      ATOM_SCALES_PATH="$ATOM_SCALES_PATH" \
      TRAIN_CACHE_PATH="$TRAIN_CACHE_PATH" \
      EVAL_CACHE_PATH="$EVAL_CACHE_PATH" \
      NUM_SCALE_SAMPLES="$NUM_SCALE_SAMPLES" \
      NUM_CAND="$NUM_CAND" \
      NUM_TRAIN_SCENARIOS="$NUM_TRAIN_SCENARIOS" \
      NUM_EVAL_SCENARIOS="$NUM_EVAL_SCENARIOS" \
      REBUILD_TRAJDATA_CACHE="$REBUILD_TRAJDATA_CACHE" \
      bash scripts/pipeline/rebuild_mapaware_inputs.sh
  fi

  sync_canonical_artifacts

  if [[ "$DO_SANITY" == "1" ]]; then
    run_logged 02_clearance_sanity python -u scripts/tools/debug_clearance_atoms.py \
      --data_root "$DATA_ROOT" \
      --cache_dir "$CACHE_DIR" \
      --split nusc_trainval-train \
      --num_samples "$SANITY_SAMPLES" \
      --batch_size 8 \
      --thresholds 1,2,3,5
  fi

  if [[ "$DO_STATIC" == "1" ]]; then
    run_logged 03_train_static python -u scripts/train/train_offline_preference.py \
      --data_root "$DATA_ROOT" \
      --cache_dir "$CACHE_DIR" \
      --batch_size 4 \
      --num_workers "$NUM_WORKERS" \
      --num_candidates "$STATIC_NUM_CANDIDATES" \
      --num_scenarios "$STATIC_NUM_SCENARIOS" \
      --cache_path "$TRAIN_CACHE_PATH" \
      --lr "$STATIC_LR" \
      --epochs "$STATIC_EPOCHS" \
      --l1_reg "$STATIC_L1_REG" \
      --device "$DEVICE" \
      --atom_scales_path "$ATOM_SCALES_PATH" \
      --split nusc_trainval-train \
      --output_path "$OFFLINE_WEIGHTS_PATH"
    link_or_copy "$OFFLINE_WEIGHTS_PATH" "$ROOT/models/offline_weights.npy"
  fi

  if [[ "$DO_RERANKER" == "1" ]]; then
    run_logged 04_train_reranker_safe python -u scripts/train/train_reranker.py \
      --data_root "$DATA_ROOT" \
      --cache_dir "$CACHE_DIR" \
      --batch_size 4 \
      --num_workers "$NUM_WORKERS" \
      --num_scenarios "$RERANKER_NUM_SCENARIOS" \
      --cache_path "$TRAIN_CACHE_PATH" \
      --epochs "$RERANKER_EPOCHS" \
      --lr "$RERANKER_LR" \
      --train_batch_size "$RERANKER_TRAIN_BATCH_SIZE" \
      --lambda_safe "$RERANKER_LAMBDA_SAFE" \
      --safety_temp "$RERANKER_SAFETY_TEMP" \
      --atom_scales_path "$ATOM_SCALES_PATH" \
      --output_path "$RERANKER_SAFE_PATH" \
      --trajectron_conf "$CONF_PATH" \
      --trajectron_model_dir "$MODEL_DIR" \
      --trajectron_epoch "$BASE_EPOCH" \
      --embedding_dim 64 \
      --split nusc_trainval-train
    link_or_copy "$RERANKER_SAFE_PATH" "$ROOT/models/reranker_safe.pt"
  fi

  if [[ "$DO_CAMP_FINETUNE" == "1" ]]; then
    run_logged 05_train_camp_and_finetune env \
      ROOT="$ROOT" \
      DATA_ROOT="$DATA_ROOT" \
      CACHE_DIR="$CACHE_DIR" \
      MODEL_DIR="$MODEL_DIR" \
      CONF_PATH="$CONF_PATH" \
      BASE_EPOCH="$BASE_EPOCH" \
      RUN_TAG="$RUN_TAG" \
      ATOM_SCALES_PATH="$ATOM_SCALES_PATH" \
      TRAIN_CACHE_PATH="$TRAIN_CACHE_PATH" \
      EVAL_CACHE_PATH="$EVAL_CACHE_PATH" \
      CAMP_ITERS="$CAMP_ITERS" \
      NUM_CAND="$NUM_CAND" \
      CAMP_NUM_SCENARIOS="$CAMP_NUM_SCENARIOS" \
      CAMP_PRIOR_REG="$CAMP_PRIOR_REG" \
      CAMP_ANCHOR_WEIGHT="$CAMP_ANCHOR_WEIGHT" \
      CAMP_RISK_TYPE="$CAMP_RISK_TYPE" \
      CAMP_ALPHA="$CAMP_ALPHA" \
      CAMP_MASTER_BATCH_SIZE="$CAMP_MASTER_BATCH_SIZE" \
      CAMP_MAX_CUTS_PER_SCENE="$CAMP_MAX_CUTS_PER_SCENE" \
      MAX_CUTS_PER_SCENE="$CAMP_MAX_CUTS_PER_SCENE" \
      CAMP_OUTPUT_PATH="$CAMP_OUTPUT_PATH" \
      OFFLINE_WEIGHTS_PATH="$OFFLINE_WEIGHTS_PATH" \
      FT_CHECKPOINT_PREFIX="$FT_CHECKPOINT_PREFIX" \
      FINETUNE_TRAIN_EPOCHS="$FINETUNE_TRAIN_EPOCHS" \
      FINETUNE_EVAL_EPOCHS="$FINETUNE_EVAL_EPOCHS" \
      FINETUNE_LOSS_MODE="$FINETUNE_LOSS_MODE" \
      FINETUNE_RISK_TYPE="$FINETUNE_RISK_TYPE" \
      FINETUNE_CVAR_ALPHA="$FINETUNE_CVAR_ALPHA" \
      FINETUNE_WARMUP_EPOCHS="$FINETUNE_WARMUP_EPOCHS" \
      FINETUNE_RAMP_EPOCHS="$FINETUNE_RAMP_EPOCHS" \
      FINETUNE_MAX_BATCHES_PER_EPOCH="$FINETUNE_MAX_BATCHES_PER_EPOCH" \
      EVAL_ATOM_CLIP="$EVAL_ATOM_CLIP" \
      FINETUNE_SAFETY_RADIUS="$SAFETY_RADIUS" \
      FINETUNE_CLEARANCE_SOFT_MARGIN="$CLEARANCE_SOFT_MARGIN" \
      SAFETY_RADIUS="$SAFETY_RADIUS" \
      CLEARANCE_SOFT_MARGIN="$CLEARANCE_SOFT_MARGIN" \
      LIVE_LOGS="${LIVE_LOGS:-1}" \
      bash scripts/pipeline/run_joint_camp_finetune.sh

    if [[ -e "$CAMP_OUTPUT_PATH" && ! -e "$CAMP_SELECT_PATH" ]]; then
      cp -f "$CAMP_OUTPUT_PATH" "$CAMP_SELECT_PATH"
    elif [[ -e "$CAMP_SELECT_PATH" ]]; then
      link_or_copy "$CAMP_SELECT_PATH" "$CANON_CAMP_SELECT_PATH"
    fi
  fi

  if [[ "$DO_FINETUNE_EVALS" == "1" ]]; then
    run_logged 05b_eval_finetune_rows eval_finetune_rows
  fi

  if [[ "$DO_CAMP_PREDS" == "1" ]]; then
    run_logged 05c_eval_camp_select eval_camp_preds
  fi

  if [[ "$DO_BASELINE_PREDS" == "1" ]]; then
    run_logged 06_eval_top1_static_oracle python -u scripts/eval/run_heuristics.py \
      --cache_path "$EVAL_CACHE_PATH" \
      --output_dir "$RESULTS_DIR" \
      --offline_weights_path "$OFFLINE_WEIGHTS_PATH" \
      --atom_scales_path "$ATOM_SCALES_PATH" \
      --atom_clip "$EVAL_ATOM_CLIP"
  fi

  if [[ "$DO_RERANKER_PREDS" == "1" ]]; then
    run_logged 07_eval_reranker_safe eval_reranker_preds
  fi

  if [[ "$DO_METRICS" == "1" ]]; then
    local pred_files=()
    local maybe_pred
    for maybe_pred in \
      "$RESULTS_DIR/camp_select_it${CAMP_ITERS}_${RUN_TAG}_preds.json" \
      "$RESULTS_DIR/pred_top1_preds.json" \
      "$RESULTS_DIR/select_static_preds.json" \
      "$RESULTS_DIR/oracle_minade_preds.json" \
      "$RESULTS_DIR/reranker_safe_preds.json"; do
      if [[ -f "$maybe_pred" ]]; then
        pred_files+=("$maybe_pred")
      fi
    done
    if [[ "${#pred_files[@]}" -eq 0 ]]; then
      die "No cache-based prediction files found for current eval flow in $RESULTS_DIR"
    fi

    for preds_path in "${pred_files[@]}"; do
      local base_name
      base_name="$(basename "$preds_path" _preds.json)"
      run_logged "08_metrics_${base_name}" python -u scripts/eval/unified_eval.py \
        --cache_path "$EVAL_CACHE_PATH" \
        --preds_path "$preds_path" \
        --atom_scales_path "$ATOM_SCALES_PATH" \
        --atom_clip "$EVAL_ATOM_CLIP" \
        --output_path "$RESULTS_DIR/${base_name}_metrics.json"
    done

    local table_metric_files=()
    local maybe_metric
    for maybe_metric in \
      "$RESULTS_DIR/camp_select_it${CAMP_ITERS}_${RUN_TAG}_metrics.json" \
      "$RESULTS_DIR/finetune_safe_e5_${RUN_TAG}_metrics.json" \
      "$RESULTS_DIR/finetune_safe_e10_${RUN_TAG}_metrics.json" \
      "$RESULTS_DIR/finetune_safe_e20_${RUN_TAG}_metrics.json" \
      "$RESULTS_DIR/finetune_safe_e60_${RUN_TAG}_metrics.json" \
      "$RESULTS_DIR/finetune_safe_e90_${RUN_TAG}_metrics.json" \
      "$RESULTS_DIR/finetune_safe_e120_${RUN_TAG}_metrics.json" \
      "$RESULTS_DIR/finetune_camp_select_e5_${RUN_TAG}_metrics.json" \
      "$RESULTS_DIR/finetune_camp_select_e10_${RUN_TAG}_metrics.json" \
      "$RESULTS_DIR/finetune_camp_select_e20_${RUN_TAG}_metrics.json" \
      "$RESULTS_DIR/finetune_camp_select_e60_${RUN_TAG}_metrics.json" \
      "$RESULTS_DIR/finetune_camp_select_e90_${RUN_TAG}_metrics.json" \
      "$RESULTS_DIR/finetune_camp_select_e120_${RUN_TAG}_metrics.json" \
      "$RESULTS_DIR/pred_top1_metrics.json" \
      "$RESULTS_DIR/select_static_metrics.json" \
      "$RESULTS_DIR/oracle_minade_metrics.json" \
      "$RESULTS_DIR/reranker_safe_metrics.json"; do
      if [[ -f "$maybe_metric" ]]; then
        table_metric_files+=("$maybe_metric")
      fi
    done
    if [[ "${#table_metric_files[@]}" -eq 0 ]]; then
      die "No metric files found for current Table-2 flow in $RESULTS_DIR"
    fi
    local timing_args=()
    if [[ -f "$TIME_COMPARE_JSON" ]]; then
      timing_args=(--timing_compare_files "$TIME_COMPARE_JSON")
    fi

    run_logged 09_print_table bash -lc \
      "python -u scripts/eval/print_table.py --results_dir '$RESULTS_DIR' --metric_files ${table_metric_files[*]@Q} ${timing_args[*]@Q} | tee '$RESULTS_DIR/table2_${RUN_TAG}.txt'"
  fi

  echo
  echo "Done. Logs: $LOG_DIR"
  echo "Metrics/results: $RESULTS_DIR"
}

main "$@"
