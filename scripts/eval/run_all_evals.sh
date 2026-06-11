#!/bin/bash

echo "=== Running All Evaluations ==="

# 1. Evaluate Pred-Top1
if [ -f "results/pred_top1_preds.json" ]; then
    echo "Evaluating Pred Top1..."
    python scripts/eval/unified_eval.py --cache_path data/cached_eval_batch.pkl --preds_path results/pred_top1_preds.json --output_path results/pred_top1_metrics.json
fi

# 2. Evaluate Select-Static
if [ -f "results/select_static_preds.json" ]; then
    echo "Evaluating Select Static..."
    python scripts/eval/unified_eval.py --cache_path data/cached_eval_batch.pkl --preds_path results/select_static_preds.json --output_path results/select_static_metrics.json
fi

# 3. Evaluate Oracle-MinADE
if [ -f "results/oracle_minade_preds.json" ]; then
    echo "Evaluating Oracle MinADE..."
    python scripts/eval/unified_eval.py --cache_path data/cached_eval_batch.pkl --preds_path results/oracle_minade_preds.json --output_path results/oracle_minade_metrics.json
fi

# 4. Evaluate Reranker Safe
if [ -f "results/reranker_safe_preds.json" ]; then
    echo "Evaluating Reranker Safe..."
    python scripts/eval/unified_eval.py --cache_path data/cached_eval_batch.pkl --preds_path results/reranker_safe_preds.json --output_path results/reranker_safe_metrics.json
fi

# 5. Evaluate CAMP Select
if [ -f "results/camp_select_preds.json" ]; then
    echo "Evaluating CAMP Select..."
    python scripts/eval/unified_eval.py --cache_path data/cached_eval_batch.pkl --preds_path results/camp_select_preds.json --output_path results/camp_select_metrics.json
fi

# 6. Evaluate Finetune Baseline (if trained)
if [ -f "adaptive-prediction/experiments/nuScenes/models/nusc_mm_base_tpp-11_Sep_2022_19_15_45/finetuned_safe_60.pt" ]; then
    echo "Evaluating Finetune Safe..."
    python scripts/eval/eval_finetune.py \
      --traj_conf_path adaptive-prediction/experiments/nuScenes/models/nusc_mm_base_tpp-11_Sep_2022_19_15_45/config.json \
      --traj_model_dir adaptive-prediction/experiments/nuScenes/models/nusc_mm_base_tpp-11_Sep_2022_19_15_45 \
      --finetuned_epoch 60
fi

echo "=== Rendering Table 2 ==="
python scripts/eval/print_table.py --results_dir results
