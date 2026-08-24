# CAMP Core: Conic Atom Meta-Policy

CAMP (Conic Atom Meta-Policy) is a decision-layer adaptation method for frozen
trajectory generators. It changes neither the upstream generator nor the
realized candidate pool: it learns how to choose among the alternatives already
available in each scene.

This repository contains two CAMP instantiations. Trajectron++ supplies
open-loop prediction candidates; Diffusion Planner (DP) supplies timed ego-plan
candidates that already encode interactions among the ego vehicle, agents, and
map. In both cases, CAMP operates only at the final decision layer. The
checked-in deployment bundle targets Diffusion Planner.

## Method overview

For scene $i$, the frozen generator returns an ordered pool
$\{\tau_{ik}\}_{k=1}^{K}$. CAMP computes a lower-is-better score from
deployment-available candidate atoms $x_{ik}$. The Diffusion Planner
implementation exposes two versions:

- **Fixed-weight CAMP:** $s_{ik}=x_{ik}^{\mathsf T}b_{p(i)}$.
- **Scene-conditioned CAMP:**
  $s_{ik}=x_{ik}^{\mathsf T}\Theta_{p(i)}[\phi_i;1]$.

Here, $p(i)$ is the endpoint-status pattern and $\phi_i$ is a frozen generator
representation; the checked-in DP model uses a 256-dimensional masked-token
mean. The selected trajectory is $\arg\min_k s_{ik}$, with ties resolved by the
original candidate order.

For the checked-in DP model, training compares a logged human demonstration
with the fixed candidate pool. A convex calibration fit assigns nonnegative
weights to offline comparison attributes, with total safety weight no lower
than comfort and comfort no lower than the remaining criteria. The minimum
calibrated-cost candidate set is then frozen as the within-pool target. CAMP
fits that target with a ranking hinge, CVaR tail risk, and quadratic
regularization; finite-candidate separation supplies the Benders cuts. Only
decision-time atoms and, for the conditioned model, the frozen encoder
representation enter the online score.

## Current Diffusion Planner configuration

The checked-in K=8 deployment bundle was fitted on 50,000 Boston/Pittsburgh
scenes:

- eight ordered DP candidates, with `candidate0` equal to `row0`;
- 15 base decision atoms covering safety, rules, progress, and comfort, plus an
  optional previous-plan continuity atom, for at most 16 active coordinates;
- 24 endpoint-status patterns;
- endpoint-local `observed`, `not_applicable`, and `typed_missing` states;
- no zero filling for unavailable endpoints;
- fixed-weight and scene-conditioned CAMP checkpoints;
- raw affine scoring without offline calibration or logged futures at inference
  time.

The compact bundle is stored in
[`artifacts/camp_v26_k8_50k/`](artifacts/camp_v26_k8_50k/). The frozen DP model
is not duplicated: scene-conditioned CAMP reuses the encoder representation
from the planner's existing forward pass.

## CAMP selector for Diffusion Planner

CAMP is designed to occupy Diffusion Planner's candidate-selection stage:

```text
DP candidate generation -> CAMP selector -> selected DP trajectory
```

A complete DP adapter should pass one planning tick to the selector. The
selector then extracts the ordered K=8 ego candidates and candidate-aligned
actor predictions, materializes the observable CAMP atoms and endpoint states,
reuses the masked DP encoder representation when scene conditioning is enabled,
and returns one original DP candidate unchanged.

`DiffusionPlannerCAMPSelector` owns atom materialization, masked scene pooling,
weight loading, scoring, and previous-plan continuity. The DP node supplies its
native prediction tensors and current map/planner context once per tick; it
does not construct CAMP atom vectors itself.

```python
from camp_core.integrations.diffusion_planner_v26_selector import (
    DiffusionPlannerCAMPSelector,
    DiffusionPlannerCAMPTick,
)

selector = DiffusionPlannerCAMPSelector.from_directory(
    "artifacts/camp_v26_k8_50k"
)

tick = DiffusionPlannerCAMPTick(
    identity=planning_tick_identity,
    prediction=out["prediction"],
    encoder_tokens=encoding,
    token_masks=encoder_token_masks,
    neighbor_history=raw_inputs["neighbor_agents_past"][0],
    static_objects=raw_inputs["static_objects"][0],
    ego_shape=raw_inputs["ego_shape"][0],
    route_lanes=raw_inputs["route_lanes"][0],
    route_speed_limits=raw_inputs["route_lanes_speed_limit"][0],
    route_has_speed_limits=raw_inputs["route_lanes_has_speed_limit"][0],
    route_atom_context=map_context.route_atom_context,
    signal_authority=map_context.signal_authority,
    drivable_area_geometry=map_context.drivable_area_geometry,
    drivable_area_source_authority=map_context.drivable_area_source_authority,
    origin_seconds=planning_time_seconds,
    ego_x=ego_state.x,
    ego_y=ego_state.y,
    ego_yaw=ego_state.yaw,
    current_speed_mps=ego_state.speed,
)

decision = selector.select(tick, mode="scene")
selected_trajectory = decision.selected_trajectory
```

Use `mode="fixed"` for fixed-weight CAMP; its tick may omit encoder tokens and
masks. Both modes return an unchanged copy of the selected DP trajectory
together with its selected row, candidate scores, active weights, active atoms,
and status pattern. The selector retains only the previous selected plan needed
by the continuity atom; call `selector.reset()` when a route or planning episode
ends. Offline preference labels and future trajectories are never read by this
interface.

Full interface details are in
[`docs/diffusion_planner_v26_camp_reranker.md`](docs/diffusion_planner_v26_camp_reranker.md).

## Diffusion Planner training and evaluation flow

1. Run the frozen generator for each scene or planning tick to create an ordered
   candidate pool.
2. Materialize the deployment atoms and endpoint states for every candidate.
3. Compare the logged human demonstration with the generated alternatives,
   calibrate the offline preference weights, and freeze the within-pool target
   set.
4. Train fixed-weight and scene-conditioned CAMP against the same frozen targets;
   the latter additionally uses the frozen encoder representation.
5. Evaluate the selected existing trajectories with paired metrics. Safety,
   comfort, progress, displacement error, feasibility, continuity, and latency
   remain separate result families.
6. Deploy only the learned decision weights and atom scales. Calibration
   attributes, target sets, and logged futures are excluded from online
   selection.

This separation is central to CAMP: offline demonstration evidence supervises
the decision rule during training, while deployment uses only observable
candidate and scene features.

## Repository layout

- [`camp_core/`](camp_core/): CAMP atoms, scoring models, optimization code, and
  the deployable DP reranker.
- [`artifacts/camp_v26_k8_50k/`](artifacts/camp_v26_k8_50k/): compact final K=8
  deployment parameters.
- [`scripts/`](scripts/): experiment materialization, training, and evaluation
  programs.
- [`docs/`](docs/): the current Diffusion Planner reranker interface.
- [`adaptive-prediction/`](adaptive-prediction/): the Trajectron++ and trajdata
  integration used in the prediction setting.

Large datasets, generated candidate pools, experiment logs, and intermediate
checkpoints are not part of the repository.

## Environments

The Diffusion Planner and Trajectron++ paths use separate environments. Do not
install the repository-level Trajectron++ requirements into the DP environment.

### Diffusion Planner environment

Keep the Python, PyTorch, CUDA, and planner dependencies required by the
upstream DP checkout. From this repository, add only the CAMP package to that
environment:

```bash
conda activate <your-dp-environment>
python -m pip install --no-deps -e ./camp_core
```

The checked-in reranker uses NumPy and SciPy already present in the DP
environment. Add `pyproj>=3.6` and `Shapely>=2.0` only when the DP-side atom
materializer needs the nuPlan geometry utilities. The repository-level
[`requirements.txt`](requirements.txt) is not used by this environment.

### Trajectron++ environment

Use a separate Python 3.9 environment for the original Trajectron++ experiments
and their older dependency versions:

```bash
conda create --name camp-trajectron python=3.9 -y
conda activate camp-trajectron
python -m pip install -r requirements.txt
```

Then follow the submodule and editable-install steps in
[`adaptive-prediction/README.md`](adaptive-prediction/README.md). This
environment is for Trajectron++ reproduction and is not required to load the DP
deployment bundle.

## Tests

The DP selector, reranker, and sparse endpoint schema can be checked with:

```bash
cd camp_core
python -m pytest \
  tests/test_diffusion_planner_v26_camp_reranker.py \
  tests/test_diffusion_planner_v26_selector.py \
  tests/test_diffusion_planner_v26_sparse_schema.py
```

## License

This repository is released under the [MIT License](LICENSE).
