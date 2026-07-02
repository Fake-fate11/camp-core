# CAMP Core: Corrective Adaptation for Motion Prediction

This repository implements CAMP, a post-hoc trajectory-selection framework for adapting motion prediction outputs with explicit safety atoms and an offline bi-level optimization loop.

## Repository Scope

The code in this checkout has two layers:

- `camp_core/`: the CAMP package itself, including atoms, mapping heads, CVXPY/Torch outer masters, and solver utilities.
- `adaptive-prediction/`: the adapted Trajectron++ / trajdata codebase used to extract scene embeddings, candidate trajectories, maps, and nuScenes data.
- `scripts/`: project-level training, cache-building, evaluation, and experiment orchestration scripts.
- `docs/`: implementation notes, including the CAMP computational graph.

Generated data, checkpoints, plots, slide decks, archives, and session exports are intentionally ignored by `.gitignore`; they should not be uploaded when the goal is to sync code only.

## Environment Setup

Use Python 3.9. The pinned dependency stack comes from the Trajectron++ / trajdata side of the project, so newer Python versions are more likely to hit compatibility issues.

```bash
conda create -n camp python=3.9 -y
conda activate camp

# Installs the combined CAMP + Trajectron++ experiment stack.
pip install -r requirements.txt

# l5kit is installed without dependencies to avoid downgrading numpy.
pip install --no-dependencies l5kit==1.5.0
```

Install the local packages in editable mode from the project root:

```bash
cd adaptive-prediction/unified-av-data-loader
pip install -e .

cd ..
pip install -e .

cd ..
pip install -e camp_core
```

Several scripts set this automatically, but it is safe to export it in shell sessions as well:

```bash
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
```

## Dependency Groups

`requirements.txt` is intentionally broad because the main experiment path uses CAMP, Trajectron++, trajdata, nuScenes, plotting, and baseline utilities in one environment.

| Group | Packages | Why they are needed |
| --- | --- | --- |
| CAMP core only | `numpy`, `scipy`, `torch`, `cvxpy` | CAMP atoms, mapping heads, CVXPY / Benders masters, Torch-based scoring, metrics, and solver utilities. |
| CAMP scripts and reporting | `tqdm`, `pandas`, `matplotlib`, `seaborn` | Progress bars, metrics tables, experiment summaries, debugging plots, and qualitative visualization scripts. |
| Trajectron++ / trajdata adaptation | `dill`, `pyarrow`, `zarr`, `kornia`, `pyquaternion`, `orjson`, `ncls`, `pathos`, `pykalman`, `wandb` | Required by the adapted Trajectron++ stack, trajdata preprocessing, model loading, logging, and candidate generation. |
| nuScenes / map stack | `nuscenes-devkit`, `opencv-python`, `opencv-contrib-python-headless`, `protobuf==3.19.4`, `pymap3d`, `transforms3d`, `pyyaml`, `ptable`, `shapely`, `typing_extensions` | Required for nuScenes data access, map/raster/vector-map handling, geometry transforms, and compatibility with the older data stack. |
| Lyft / l5kit compatibility | `imageio`, `bokeh`, `gym`, `l5kit==1.5.0` | Needed because the upstream adaptive-prediction/trajdata environment still includes Lyft/L5Kit support. Install `l5kit` with `--no-dependencies`. |
| Development only | `black`, `isort`, `pytest`, `pytest-xdist`, `notebook` | Formatting, tests, and interactive notebooks; not required for CAMP runtime inference. |

If you only need to inspect or run CAMP on an already-built cache, the practical minimum is the CAMP core group plus `tqdm`. If you need to rebuild caches, evaluate against nuScenes, or run finetuning, install the full `requirements.txt` stack and the editable Trajectron++ packages.

## Runtime Configuration

The historical full runs used this server layout:

```bash
ROOT=/root/autodl-tmp/camp_core
DATA_ROOT=/root/autodl-tmp/dataset
CACHE_DIR=/root/autodl-tmp/.unified_data_cache
MODEL_DIR=/root/autodl-tmp/camp_core/adaptive-prediction/experiments/nuScenes/models/nusc_adaptive_tpp_scratch-01_Apr_2026_12_27_02
BASE_EPOCH=20
```

Common experiment knobs:

```bash
RUN_TAG=mapaware_clearance_v2
NUM_CAND=12
CAMP_ITERS=100
FINETUNE_TRAIN_EPOCHS=120
FINETUNE_EVAL_EPOCHS="60 90 120"
EVAL_ATOM_CLIP=10.0
```

The later K=50 result path used run tags such as `mapaware_clearance_v2_cvxpy_full_ft20_k50`, but the same environment variables control the scripts.

## Data Setup

Follow `adaptive-prediction/README.md` for nuScenes and trajdata setup. For CAMP scripts, the important paths are:

- `DATA_ROOT`: raw nuScenes dataset root.
- `CACHE_DIR`: trajdata cache directory.
- `MODEL_DIR`: Trajectron++ model directory containing `config.json` and `model_registrar-*.pt`.
- `BASE_EPOCH`: base checkpoint epoch; historical CAMP runs used epoch `20`.

After data and the base Trajectron++ checkpoint are available, rebuild map-aware CAMP inputs:

```bash
ROOT=/root/autodl-tmp/camp_core \
DATA_ROOT=/root/autodl-tmp/dataset \
CACHE_DIR=/root/autodl-tmp/.unified_data_cache \
MODEL_DIR=/root/autodl-tmp/camp_core/adaptive-prediction/experiments/nuScenes/models/nusc_adaptive_tpp_scratch-01_Apr_2026_12_27_02 \
BASE_EPOCH=20 \
RUN_TAG=mapaware_clearance_v2 \
NUM_SCALE_SAMPLES=20000 \
NUM_TRAIN_SCENARIOS=-1 \
NUM_EVAL_SCENARIOS=-1 \
REBUILD_TRAJDATA_CACHE=1 \
bash scripts/pipeline/rebuild_mapaware_inputs.sh
```

Check the printed `Map source counts`; `vector_map` should dominate. Rebuilding the cache does not require retraining the base Trajectron++ model, but CAMP and finetuning results should be regenerated from the rebuilt cache for an apples-to-apples comparison.

## Pipeline Overview

The CAMP-Select computational graph is summarized in [`docs/camp_computational_graph.md`](docs/camp_computational_graph.md). The diagram separates the shared Trajectron++ / atom-extraction path, the offline training-time Benders optimization loop, and the one-shot inference-time selector.

The current fixed TiERIV Diffusion Planner integration status is summarized in
[`docs/diffusion_planner_current_status.md`](docs/diffusion_planner_current_status.md).
The current append-only audit for new writes is
[`docs/diffusion_planner_v14_iteration_audit.md`](docs/diffusion_planner_v14_iteration_audit.md);
`docs/diffusion_planner_v13_iteration_audit.md` remains historical evidence and
the v14 rollover source.

The TIER IV Diffusion Planner simulator bridge is documented in
[`docs/diffusion_planner_integration.md`](docs/diffusion_planner_integration.md).
It generates multiple Diffusion Planner ego candidates, selects one with CAMP,
and returns the selected trajectory to the upstream perfect/MPC tracker without
requiring a ROS runtime.
The first strictly paired four-way benchmark is summarized in
[`docs/diffusion_planner_formal_v4_results.md`](docs/diffusion_planner_formal_v4_results.md).

### 1. Atom Scale Calibration

Script: `scripts/tools/compute_atom_scales.py`

Computes normalization scales for driver atoms.

- Input: nuScenes data, Trajectron++ checkpoint, candidate trajectories.
- Output: `models/production/atom_scales_<RUN_TAG>.json`.

### 2. Cache Building

Script: `scripts/data_gen/cache_dataset.py`

Extracts scene embeddings, candidate pools, atom vectors, hard feasibility masks, and ground-truth atoms.

- Output: `data/cached_train_batch_<RUN_TAG>.pkl` and `data/cached_eval_batch_<RUN_TAG>.pkl`.

### 3. Offline Preference Learning

Script: `scripts/train/train_offline_preference.py`

Learns static prior weights used by Select-Static and as a CAMP anchor.

- Input: cached data and atom scales.
- Output: `models/<RUN_TAG>/offline_weights.npy` or `models/offline_weights.npy`.

### 4. CAMP-Select Training

Script: `scripts/train/train_camp_select.py`

Trains the scene-conditioned linear map `Theta` with CVaR risk and a CVXPY Benders master.

- Input: cached training data, atom scales, optional offline weights.
- Output: CAMP checkpoint such as `models/camp_select_linear_it100_<RUN_TAG>.pt`.

### 5. Finetune-Safe Baseline

Script: `adaptive-prediction/experiments/nuScenes/train_finetune_safe.py`

Finetunes the Trajectron++ predictor with a CAMP-aligned safety loss. This is not required for CAMP itself; it is the apples-to-apples neural finetuning baseline.

### 6. Evaluation

Primary scripts:

- `scripts/eval/eval_camp_select.py`
- `scripts/eval/eval_finetune.py`
- `scripts/eval/eval_finetune_camp_select.py`
- `scripts/eval/run_heuristics.py`
- `scripts/eval/unified_eval.py`
- `scripts/eval/print_table.py`

For the joint CAMP + finetune workflow:

```bash
ROOT=/root/autodl-tmp/camp_core \
DATA_ROOT=/root/autodl-tmp/dataset \
CACHE_DIR=/root/autodl-tmp/.unified_data_cache \
MODEL_DIR=/root/autodl-tmp/camp_core/adaptive-prediction/experiments/nuScenes/models/nusc_adaptive_tpp_scratch-01_Apr_2026_12_27_02 \
BASE_EPOCH=20 \
RUN_TAG=mapaware_clearance_v2 \
CAMP_ITERS=100 \
FINETUNE_TRAIN_EPOCHS=120 \
FINETUNE_EVAL_EPOCHS="60 90 120" \
bash scripts/pipeline/run_joint_camp_finetune.sh
```

For the fuller Table-2 style rebuild:

```bash
bash scripts/pipeline/run_table2_mapaware_clearance_full.sh
```
