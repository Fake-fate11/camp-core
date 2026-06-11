#!/usr/bin/env bash
set -euo pipefail

THETA_OUTPUT_DIR="${THETA_OUTPUT_DIR:-/root/autodl-tmp/camp_dp_assets/camp_dp_scene_theta_v1}"
LINES="${LINES:-80}"
TRAIN_LOG="$THETA_OUTPUT_DIR/train_dp_scene_theta.log"
PID_FILE="$THETA_OUTPUT_DIR/train_dp_scene_theta.pid"
SUMMARY="$THETA_OUTPUT_DIR/training_summary.json"

printf 'THETA_OUTPUT_DIR=%s\n' "$THETA_OUTPUT_DIR"

if [[ -f "$PID_FILE" ]]; then
  pid="$(cat "$PID_FILE")"
  if kill -0 "$pid" >/dev/null 2>&1; then
    printf 'status=running pid=%s\n' "$pid"
  else
    printf 'status=not-running last_pid=%s\n' "$pid"
  fi
else
  printf 'status=unknown pid_file_missing=%s\n' "$PID_FILE"
fi

if [[ -f "$TRAIN_LOG" ]]; then
  printf '\n--- log tail (%s lines) ---\n' "$LINES"
  tail -n "$LINES" "$TRAIN_LOG"
else
  printf 'train log missing: %s\n' "$TRAIN_LOG"
fi

if [[ -f "$SUMMARY" ]]; then
  printf '\n--- summary ---\n'
  python - "$SUMMARY" <<'PY'
import json
import sys
from pathlib import Path

summary = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
keys = [
    "training_type",
    "num_records",
    "num_candidates",
    "feature_dim",
    "checkpoint_path",
    "atom_scales_path",
    "final_metrics",
]
print(json.dumps({key: summary.get(key) for key in keys}, indent=2))
PY
fi
