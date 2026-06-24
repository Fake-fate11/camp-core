# DP-CAMP Benders-Compatible Atom Audit

Date: 2026-06-24

## Scope

This audit checks only whether the currently deployed CAMP atom schemas can be
kept in the fixed-candidate Diffusion Planner reranker:

```text
DP native fixed candidates Y_k
-> CAMP atom and feasibility evaluation
-> score = a_k^T w
-> argmin selected_index
```

It does not authorize replay, formal seeds, CAMP retraining, online promotion,
atom promotion, DP modification, safety benefit claims, or CAMP-over-DP Top-1
claims.

## Heads

```text
local HEAD = ff56d1e157f1f03056396e458ad51446d2c29480
origin/main = ff56d1e157f1f03056396e458ad51446d2c29480
branch = main
```

Unrelated untracked handoff/session files are present and intentionally out of
scope.

## Source Hashes

```text
6b964595bcd50cf10e5edfbdebef2a8cc6b1494990103f6f66bc76d6498fcde7  camp_core/camp_core/integrations/diffusion_planner.py
a92bf52bc537fcb82291922eaa1ca6a0232649ee7988efc6102ee18425b09f99  camp_core/camp_core/atoms/driver_atoms.py
cb57206ad42fe2c3905060d5c72e9a1eeaab01c5b0327814a1723b50d335a8be  camp_core/camp_core/outer_master/robust_margin_master.py
d800d378572a5fd21cb4314c0184acb08807fb3cf611d0a550a7de438a574df0  scripts/integrations/run_diffusion_planner_camp_replay.py
6d71adcc1225459d5fd946a5456926a701d1fdb06bd87907eb9b1c19a624712b  scripts/integrations/run_diffusion_planner_camp_benchmark_matrix.py
d52cec8159b0ff46f0abde2c6c492806fbc3db25a2f3b89e1886c0828b1cafd2  docs/dp_camp_mathematical_contract.md
5fe5e6830af84ac9dd1477c44a4db8be317c6f807b226be4af851de24dbbdf12  docs/dp_camp_benders_formalization.md
```

## Mathematical Boundary

The controlling contract is the finite-candidate robust-margin master, not a
classical LP-dual Benders decomposition and not global convexity over DP
trajectory coordinates.

An atom can be retained only when, for a fixed planning tick, it is:

- computed from current-tick information and the fixed candidate trajectory;
- evaluated before CAMP scoring and treated as constant with respect to `w`;
- one finite nonnegative cost scalar per candidate;
- independent of learned weights, candidate rank, selected index, and
  closed-loop future outcomes;
- attached to a stable schema name and order;
- used only inside an affine score `a_k^T w`.

The finite-candidate ranking loss remains a maximum of affine functions in the
simplex weight variable. This preserves the cutting-plane/Benders-style master
used by CAMP.

## Code Anchors

- Atom schema registry:
  `camp_core/camp_core/integrations/diffusion_planner.py:42-70`.
- Legacy 9D atom computation:
  `camp_core/camp_core/atoms/driver_atoms.py:232-399`.
- DP extra atom assembly and validation:
  `camp_core/camp_core/integrations/diffusion_planner.py:2994-3113`.
- Score/mask/argmin selector:
  `camp_core/camp_core/integrations/diffusion_planner.py:3131-3178`.
- Red stopping-margin cost:
  `camp_core/camp_core/integrations/diffusion_planner.py:1538-1655`.
- DP-prior jerk-excess cost:
  `camp_core/camp_core/integrations/diffusion_planner.py:1693-1741`.
- Planned red-light cost extraction:
  `scripts/integrations/run_diffusion_planner_camp_replay.py:4464-4504`.
- Robust-margin master nonnegative atom check:
  `camp_core/camp_core/outer_master/robust_margin_master.py:356-371`.

## Atom Decisions

| Atom | Schema | Input provenance | Fixed before scoring | Finite/nonnegative evidence | Independent of w/rank/selected | Changes candidates | Affine score preserved | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `jerk_early` | legacy 9D and all DP schemas | candidate coordinates, `dt` | Yes | squared finite-difference jerk, nonnegative | Yes | No | Yes | Keep |
| `jerk_late` | legacy 9D and all DP schemas | candidate coordinates, `dt` | Yes | squared finite-difference jerk, nonnegative | Yes | No | Yes | Keep |
| `jerk_full` | legacy 9D and all DP schemas | candidate coordinates, `dt` | Yes | squared finite-difference jerk, nonnegative | Yes | No | Yes | Keep |
| `rms_acceleration` | legacy 9D and all DP schemas | candidate coordinates, `dt` | Yes | RMS acceleration magnitude, nonnegative | Yes | No | Yes | Keep |
| `speed_limit_margin_0_0` | legacy 9D and all DP schemas | candidate coordinates, speed limit | Yes | squared hinge speed violation | Yes | No | Yes | Keep |
| `speed_limit_margin_0_5` | legacy 9D and all DP schemas | candidate coordinates, speed limit | Yes | squared hinge speed violation | Yes | No | Yes | Keep |
| `speed_limit_margin_1_0` | legacy 9D and all DP schemas | candidate coordinates, speed limit | Yes | squared hinge speed violation | Yes | No | Yes | Keep |
| `lane_deviation` | legacy 9D and all DP schemas | candidate coordinates, route centerline | Yes | squared lane hinge | Yes | No | Yes | Keep |
| `clearance` | legacy 9D and all DP schemas | candidate coordinates, current obstacles | Yes | squared clearance intrusion hinge | Yes | No | Yes | Keep |
| `progress_shortfall` | `dp_camp_v7_10d` and later | fixed candidate progress, feasibility mask | Yes | `max(reference_progress - progress, 0)` | Yes | No | Yes | Keep |
| `planned_red_light_cost` | `dp_camp_v8_12d` and later | current-tick DP reward red-light field | Yes | `max(-reward.red_light, 0)` and selector clamps nonnegative | Yes | No | Yes | Keep |
| `planned_lateral_acceleration_cost` | `dp_camp_v8_12d` and later | candidate kinematics, `dt` | Yes | mean absolute lateral acceleration, clamped nonnegative | Yes | No | Yes | Keep |
| `red_stopping_margin_cost` | `dp_camp_v9_13d` and later | current red route points and candidate kinematics | Yes | stopping-envelope speed-excess squared integral | Yes | No | Yes | Keep |
| `dp_prior_jerk_excess_cost` | `dp_camp_v10_14d` | candidate kinematics, candidate 0 reference, `dt` | Yes | `max(mean_jerk_norm - mean_jerk_norm[0], 0)` | Yes | No | Yes | Keep |

## Rejected Non-Atom Routes

The following remain outside the deployable CAMP mainline:

- `reference_blend`;
- candidate guidance or antithetic latent sampling;
- postprocess/postselection and PerfectTracker command overrides;
- traffic-light hybrid postselection;
- underprogress relaxation;
- splice/materialized candidate generators;
- candidate0 guards and lexicographic preselection;
- closed-loop outcome labels as online inputs;
- default-off payload logging and interaction features unless later promoted
  through a separate atom gate.

The boundary commit `ff56d1e` makes the replay and benchmark-matrix main
entrypoints fail closed when these routes are enabled.

## Verification

Already run before this audit:

```text
git fetch --prune origin
git rev-parse HEAD origin/main
result: ff56d1e157f1f03056396e458ad51446d2c29480 both

python -m py_compile scripts/integrations/run_diffusion_planner_camp_replay.py scripts/integrations/run_diffusion_planner_camp_benchmark_matrix.py camp_core/tests/test_diffusion_planner_benchmark_matrix.py camp_core/tests/test_diffusion_planner_camp_replay_paper_boundary.py
exit: 0

python -m pytest camp_core/tests/test_diffusion_planner_benchmark_matrix.py camp_core/tests/test_diffusion_planner_camp_replay_paper_boundary.py -q
exit: 1
reason: existing Windows collection blocker on a missing long-path residual-comfort test file, before target tests ran

temporary rootdir target pytest with PYTHONPATH=F:\camp_core-main
result: 47 passed in 0.56s

python -m py_compile camp_core/tests/test_diffusion_planner_benders_atom_contract.py camp_core/tests/test_diffusion_planner_benchmark_matrix.py camp_core/tests/test_diffusion_planner_camp_replay_paper_boundary.py scripts/integrations/run_diffusion_planner_camp_replay.py scripts/integrations/run_diffusion_planner_camp_benchmark_matrix.py
exit: 0

temporary rootdir target pytest with PYTHONPATH=F:\camp_core-main\camp_core;F:\camp_core-main
result: 51 passed in 0.73s
```

## Decision

Keep the current deployed 9D, 10D, 12D, 13D, and 14D atom schemas as
Benders-compatible fixed-candidate atom schemas.

Reject every non-atom route listed above for replay, training, online
promotion, safety-benefit claims, and CAMP-over-DP Top-1 claims.

## Next Gate

`dp_native_candidate_tensor_provenance_payload_implementation_authorization_only`

This next gate may only decide whether to implement minimal default-off
candidate tensor provenance logging. It must not run replay, generate
candidates, rewrite trajectories, retrain CAMP, promote atoms, modify DP, or
claim safety/DP superiority.
