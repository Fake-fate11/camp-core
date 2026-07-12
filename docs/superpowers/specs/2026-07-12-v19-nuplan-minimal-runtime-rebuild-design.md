# V19 nuPlan Minimal Runtime Rebuild Design

**Date:** 2026-07-12
**Status:** Pre-approved by the user's explicit blocked-goal recovery authorization

## Goal

Recreate only `/root/autodl-tmp/camp_v19_nuplan_env` as a reproducible
Python 3.9 runtime for official nuPlan v1.2 simulation components while
keeping at least `10737418240` free bytes and leaving the fixed-DP environment
unchanged.

## Cleanup Qualification

The authorized directory was resolved and checked before deletion. The sealed
pre-delete artifact is:

`/root/autodl-tmp/camp_dp_v19_nuplan_env_cleanup_predelete_64b9ce08_20260712T131237CST`

with root SHA256
`971a3df09549cbde6f7d697cbf2db4ddc3afc62e38ad35e095f0a110ba788086`.
It records the `6453283272`-byte failed environment, no process using it,
`pip check` failure, absent `nuplan-devkit`, fixed heads, pointer state, and
preserved paths. The exact-directory deletion released `6586032128` bytes and
left `16179240960` free bytes. Its artifact/root is:

- `/root/autodl-tmp/camp_dp_v19_nuplan_env_cleanup_execution_64b9ce08_20260712T131317CST`
- `d57abac9a58a018830656a70d8a4a9f139649c0a232d65b09ec589d5c07916b8`

No other path was deleted.

## Selected Runtime Boundary

Keep the already-approved two-process boundary:

- the simulator process uses the rebuilt Python 3.9 environment and official
  nuPlan source at commit
  `ce3c323af01c0d7ec5672f7832ef53f9c679aab0`;
- the fixed-DP worker remains in `/root/autodl-tmp/dp312_venv` at DP commit
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`;
- NPZ/JSON files remain the only bridge.

The simulator harness will instantiate official `Simulation`,
`SimulationRunner`, `PerfectTrackingController`, `TracksObservation`,
`StepSimulationTimeController`, and `MetricsEngine` components directly. It
will not import the top-level `run_simulation.py`, whose orchestration-only
`pytorch_lightning.seed_everything` import would duplicate torch. Seeds remain
the preregistered values and are set explicitly by the CAMP-side harness.

This changes only orchestration, not the official simulator, scenario,
controller, observation, history propagation, or metric implementations.

## Minimal Dependency Union

The frozen direct requirements are in
`scripts/integrations/nuplan_v12_minimal_runtime_requirements.txt`. They are the
third-party closure of the official local-GPKG scenario builder, sequential
worker, simulation runner, perfect-tracking controller, tracks observation,
metric engine, and closed-loop metric implementations. The closure contains
139 internal nuPlan modules and has
`torch_present=false` / `pytorch_lightning_present=false`.

The following are forbidden in the resolved lock:

- `torch`, `torchvision`, `torch-scatter`, `torchmetrics`, `timm`;
- `pytorch-lightning`, `tensorboard`;
- `ray`, `docker`, `grpcio`, `grpcio-tools`;
- Jupyter, notebook, Selenium, pre-commit, and training-only packages.

The input intentionally omits Hydra/OmegaConf because no configuration builder
is used, and omits pyarrow because metric results are computed directly and
materialized without the official parquet aggregation callback.

## Reproducibility Gate

Before environment creation, the existing read-only
`/root/miniconda3/envs/camp` Python 3.9 resolver performs a
`--dry-run --report` with binary wheels only. It uses
`--isolated --index-url https://pypi.org/simple` so the lock is not affected by
AutoDL's incomplete machine-level mirror. Using a real Python 3.9 resolver also
prevents pip from evaluating `Requires-Python` against the Python 3.12 fixed-DP
worker. A stdlib converter emits a sorted `--require-hashes` lock. Static
review must prove:

1. every resolved item has an exact version, a wheel URL, and SHA256;
2. no forbidden package is present;
3. all frozen direct requirements appear in the lock;
4. projected post-install free space is at least `10737418240` bytes;
5. CAMP, DP, official source, current-status, and audit pointers have not
   drifted.

Only that reviewed lock may be installed. The base prefix is created with
Python 3.9, pip 21.2.4, and setuptools 59.5.0. Runtime wheels are installed
with `--isolated --index-url https://pypi.org/simple --no-deps
--require-hashes`; the fixed official source is then installed locally with
`--isolated --no-index --no-deps --no-build-isolation`.

## Fail-closed Verification

The one allowed rebuild stops without retry if any command fails, free space
drops below the hard floor, `pip check` is nonzero, a forbidden package is
installed, or the official source/runtime imports fail. A failed prefix and
all stderr/SHA evidence are retained for review.

Passing materialization requires exact Python/source provenance, a full
package lock, `pip check` exit 0, import smokes for every frozen official
component, no fixed-DP modification, and at least 10 GiB free. It does not
authorize simulator execution, holdout access, claims, promotion, deployment,
or activation.
