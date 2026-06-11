#!/usr/bin/env bash
set -euo pipefail

ASSET_DIR="${ASSET_DIR:-/root/autodl-tmp/camp_dp_assets}"
DOWNLOAD_NISHISHINJUKU="${DOWNLOAD_NISHISHINJUKU:-1}"

mkdir -p "$ASSET_DIR"
cd "$ASSET_DIR"

fetch() {
  local url="$1"
  local output="$2"
  local expected_size="$3"
  local status=0
  if [[ -f "$output" && "$(stat -c '%s' "$output")" == "$expected_size" ]]; then
    printf '%s already complete (%s bytes)\n' "$output" "$expected_size"
    return
  fi
  curl -fL --retry 10 --retry-delay 2 --connect-timeout 20 \
    -C - -o "$output" "$url" || status=$?
  if [[ "$status" -eq 22 ]]; then
    printf 'resume returned HTTP error for %s; validating existing file\n' "$output"
  elif [[ "$status" -ne 0 ]]; then
    return "$status"
  fi
}

fetch \
  "https://awf.ml.dev.web.auto/planning/models/diffusion_planner/v5.0/diffusion_planner.pth" \
  "diffusion_planner.pth" \
  "233462137"
fetch \
  "https://awf.ml.dev.web.auto/planning/models/diffusion_planner/v5.0/diffusion_planner.param.json" \
  "diffusion_planner.param.json" \
  "109201"
fetch \
  "https://autoware-files.s3.us-west-2.amazonaws.com/maps/demos/sample-map-planning.zip" \
  "sample-map-planning.zip" \
  "15888534"

printf '%s  %s\n' \
  "4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75" \
  "diffusion_planner.pth" \
  "ee3145b68fd1e1e44e532933dfe66cfee4384fbd637382c87ab5190c66a8e268" \
  "diffusion_planner.param.json" \
  "5536fce7bb8db7688fdf94ec004118b898637ad0d5b6175108b10989dd6e93b9" \
  "sample-map-planning.zip" \
  | sha256sum --check -

mkdir -p sample-map-planning
unzip -n -q sample-map-planning.zip -d sample-map-planning

if [[ "$DOWNLOAD_NISHISHINJUKU" == "1" ]]; then
  fetch \
    "https://github.com/autowarefoundation/AWSIM/releases/download/v1.1.0/nishishinjuku_autoware_map.zip" \
    "nishishinjuku_autoware_map.zip" \
    "58535865"
  printf '%s  %s\n' \
    "4b97f1070c6f7e24d6f4e74359082743bf850e7fc3a5b3b0a67392aa587bde4a" \
    "nishishinjuku_autoware_map.zip" \
    | sha256sum --check -
  mkdir -p nishishinjuku_autoware_map
  unzip -n -q nishishinjuku_autoware_map.zip -d nishishinjuku_autoware_map
fi

find "$ASSET_DIR" -maxdepth 4 -type f \
  \( -name "*.pth" -o -name "*.json" -o -name "*.osm" -o -name "*.yaml" \) \
  -printf '%p %s bytes\n' | sort
