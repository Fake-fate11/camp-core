# V19 Native-default nuPlan Closed-loop Capability Plan

**Date:** 2026-07-11
**Status:** Plan-only; no dependency installation or simulator execution is authorized by this document

## Goal

Build the smallest auditable path to compare CAMP against the fixed TiER IV
Diffusion Planner's executable default deterministic/MAP selection in official
nuPlan closed-loop simulation. This plan cannot establish a native DP Top-1
claim because the fixed commit exposes no native K-ranking path.

## Frozen Starting Evidence

- CAMP local/GitHub/AutoDL HEAD at plan start:
  `bd36037710e766855d1d7e519af6d23b355409b5`
- Fixed DP HEAD:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Evidence-gap artifact/root:
  `/root/autodl-tmp/camp_dp_v19_native_baseline_safety_evidence_gap_5a6a0976_20260711T230539CST`
  / `8d860e61165f77cc0893ad17199970f833b41be2a4d2696dd168d789f929a791`
- nuPlan mini: 64 DBs, `14351183872` DB bytes, 4 map databases.
- Free bytes at plan inventory: `16222699520`.
- Existing fixed-DP runtime: Python `3.12.3`, torch `2.8.0+cu128`.
- `/root/miniconda3/bin/conda` exists, but no Python 3.9 interpreter is
  currently installed or on PATH.
- Official nuPlan devkit is absent from the fixed-DP environment.

The official nuPlan source is frozen to tag `nuplan-devkit-v1.2`, Git commit
`ce3c323af01c0d7ec5672f7832ef53f9c679aab0`. Its official environment requests
Python 3.9 and pip 21.2.4, its `AbstractPlanner` consumes
`PlannerInitialization` and per-tick `PlannerInput`, and `run_simulation`
accepts pre-instantiated planners. Official sources:

- https://github.com/motional/nuplan-devkit/tree/nuplan-devkit-v1.2
- https://raw.githubusercontent.com/motional/nuplan-devkit/nuplan-devkit-v1.2/environment.yml
- https://raw.githubusercontent.com/motional/nuplan-devkit/nuplan-devkit-v1.2/nuplan/planning/simulation/planner/abstract_planner.py
- https://raw.githubusercontent.com/motional/nuplan-devkit/nuplan-devkit-v1.2/nuplan/planning/script/run_simulation.py
- https://raw.githubusercontent.com/motional/nuplan-devkit/nuplan-devkit-v1.2/docs/metrics_description.md

## Architecture Decision

Use two isolated processes and a simple file bridge.

1. **Simulator process:** an isolated Python 3.9 conda environment containing
   only the pinned official nuPlan v1.2 devkit requirements needed for
   simulation/metrics.
2. **Fixed-DP worker:** the unchanged
   `/root/autodl-tmp/dp312_venv` loads the fixed DP repo/checkpoint and CAMP
   code read-only.
3. **Bridge:** per-tick request and response NPZ files plus JSON metadata in a
   fresh run staging directory. No pickle, socket service, or new serialization
   dependency. File I/O is included in total planning-path latency.

This avoids installing old nuPlan hydra/numpy/torch constraints into the fixed
DP environment. It is intentionally smoke-first; no performance optimization
is added before the official simulation path works.

## Immutable Selector and Candidate Contract

Use the v18 frozen corrected14D selector root only:

`/root/autodl-tmp/camp_dp_v18_nuplan_causal_10k_static_14d_train_calibrate_79c9570b_0c22f85e`

- selector root SHA256:
  `afec0dd1e555aaf97adc43f7fa92dce86fa155489ce7fa73fdf339df0c9c35d7`
- `atom_scales.json` SHA256:
  `a4122b0fa56912818af92eacf90449633addf9872966aed975317b4307076952`
- `static_weights.npy` SHA256:
  `922ae11db719a2bda983bccf0c6bca842c37a899c4df222a1f7a5ac733285134`

At every CAMP-arm planning tick, the fixed DP emits K=8 with the v18 generation
contract: candidate 0 uses zero initial noise and candidates 1-7 use
`noise_scale=1.0`. CAMP only computes the frozen canonical 14D atoms,
feasibility mask, affine score, and argmin over feasible candidates. Candidate
tensors are hashed before and after CAMP scoring; any mismatch fails closed.

All-K-infeasible ticks preserve candidates, masks, and reasons, terminate the
CAMP scenario as a failed pair, and never force candidate 0 or use all-K
progress fallback.

## Baseline Arms and Executable Provenance Gate

The first adapter execution must be a single-tick, non-simulator provenance
smoke on one label-free input:

- native/default arm: zero-latent single DP call and the default replay output
  `[batch=0, ego=0]`;
- independent reference: the already established deterministic/MAP call on the
  identical causal input;
- required result: elementwise equality and identical trajectory SHA, source
  hashes, checkpoint SHA, config SHA, input SHA, and output SHA.

Only after this passes may the baseline be called
`DP-default deterministic/MAP baseline`. It still cannot be called native
ranked Top-1.

For each closed-loop scenario:

- baseline arm uses the executable DP default deterministic/MAP output;
- CAMP arm generates K=8 from the same fixed model/config/checkpoint each tick
  and selects one unchanged candidate;
- both arms start from the same scenario, seed, and initial state, then roll
  independently; subsequent states and tensors may diverge naturally.

## Official Simulator Smoke Freeze

- Official devkit: tag/commit above, source hash manifest required.
- Simulation mode: official `closed_loop_nonreactive_agents`.
- Ego controller: official perfect tracking controller.
- Worker: sequential, one scenario at a time, one CPU allocation; no Ray
  cluster.
- Metrics: enabled; simulation history/logs retained.
- Simulator seed: `3411`.
- DP stochastic-sample seed root: `3412`, derived per run-key/tick by SHA256.
- Cluster-bootstrap seed: `3410`, 10,000 replicates.
- Formal seeds `11/12/13`: forbidden.

Smoke selection uses label-free log/scene identifiers only. It excludes every
log and scene present in any v18 10k train/calibration/holdout manifest and
selects by SHA256 order from remaining mini logs. The target is two scenarios
from distinct logs: one normal and one interaction/critical bucket. If two
zero-overlap buckets are unavailable, stop rather than relax overlap or reopen
holdout labels.

`closed_loop_nonreactive_agents` is an official closed-loop ego simulation with
nonreactive logged traffic participants. Results must carry that exact scope;
they are not reactive-traffic or real-world safety evidence.

## Metrics and Claim Freeze

Primary metric remains lower-is-better SafetyCost v1 from
`docs/dp_camp_safety_score_v1.md`, SHA256
`5a3f6cd77bb5ff34e002321b1dbd201d2a4fd56af058fa57f7d6b8d06dffe9d3`.
Every raw component must be materialized from the paired closed-loop histories:
collision, near miss, lane violation, realized red light, planned red light,
mean jerk, mean lateral acceleration, route completion, and route shortfall.
If any component is unavailable, the SafetyCost result and claim fail closed;
an official metric cannot silently substitute for a missing SafetyCost field.

Also report official nuPlan v1.2 metrics when produced: at-fault collision,
drivable-area compliance, driving-direction compliance, TTC, progress,
speed-limit compliance, comfort, and secondary ADE/FDE/miss. Missing official
metrics remain explicitly missing.

The support rule is unchanged:

```text
hard_gate_passed=true
and ci95_high(CAMP SafetyCost v1 - DP-default SafetyCost v1) < 0
```

Report mean delta, 10,000-replicate deterministic log- and scene-cluster CI95,
CVaR90, better/tie/worse, scenario buckets, every hard gate, selector latency,
bridge latency, DP inference latency, and total planning-path latency. The
industrial latency gate uses total planning-path latency when available;
selector-only latency is descriptive.

ADE/FDE/miss are secondary trajectory-quality/non-regression results and cannot
override the primary safety result. No threshold, seed, bucket, weight, or CI
rule may change after smoke outputs are observed.

## Gate Sequence

### Gate 1: Plan static review only

Verify this plan contains the exact fixed heads, official tag/commit, selector
hashes, two-process boundary, baseline naming, K=8/no-mutation contract,
zero-overlap rule, simulator scope, metrics, seeds, and stop behavior. It must
authorize no install or execution.

### Gate 2: Dependency and disk preflight only

Run conda `--dry-run --json` for a fresh explicit-prefix Python 3.9
environment and inventory the fixed tag without installing it. Freeze expected
download/install bytes. Require at least 10 GiB free after the estimated
environment, source checkout, one failed staging root, and one successful smoke
artifact. Stop if the budget fails. Do not modify or add packages to
`dp312_venv`.

### Gate 3: Isolated source/environment materialization

Only after Gate 2 review passes, create the fixed-tag source checkout and
isolated conda environment. Record package lock, source HEAD, license, disk,
imports, and official devkit unit smoke. No DP/CAMP adapter execution yet.

### Gate 4: Adapter and provenance TDD

Implement only CAMP-side files. Tests must cover PlannerInput causal conversion,
future sentinel rejection, route/traffic-light timestamps, dt and SE(2),
immutable K=8 tensors, exact default-output equivalence, all-K-infeasible
failure, paired run keys, and latency accounting. DP code/config/weights remain
unchanged.

### Gate 5: Smoke preflight, execution, and result review

Freeze the two selected zero-overlap scenarios and all hashes before execution.
Run baseline and CAMP arms once. Independently recompute pairing, candidate
hashes, SafetyCost components, official metrics, CI inputs, and latencies.
Smoke is feasibility/directional evidence only and cannot support a broad
safety claim.

### Gate 6: Conditional non-formal scale-up

Proceed only when every smoke integrity gate passes and resources remain within
the approved existing-data budget. Otherwise emit exact dependency/data/disk/
runtime gaps and stop. No large dataset download is authorized.

## Stop Conditions

Stop before the next mutation when any of these occurs:

- CAMP/GitHub/AutoDL or fixed DP HEAD drift;
- official tag/commit or selector hash mismatch;
- fewer than two zero-overlap smoke scenarios in required buckets;
- dependency plan would leave less than 10 GiB free;
- nuPlan execution requires modifying DP or its environment;
- default deterministic equivalence fails;
- future leakage, candidate mutation, non-affine/non-simplex/non-convex logic,
  all-K fallback, or incomplete SafetyCost components;
- a related job is already running;
- the next action would reopen v18 holdout labels, download large new data, use
  Full36/formal seeds, promote, deploy, activate, replace a model, or make a
  broad native-Top-1/real-world safety claim.
