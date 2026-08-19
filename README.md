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

## Direct DP reranking

```python
from camp_core.integrations.diffusion_planner_v26_camp_reranker import (
    CAMPDPRerankingPipeline,
    build_camp_atom_artifact,
    masked_mean_scene_embedding,
)

pipeline = CAMPDPRerankingPipeline.from_directory(
    "artifacts/camp_v26_k8_50k"
)

# `candidate_atom_values` contains one K=8 vector for each observed atom.
# Unavailable endpoints remain statuses and are not assigned numeric values.
artifact = build_camp_atom_artifact(
    candidate_atom_values,
    endpoint_status,
)

selected_trajectory, result = pipeline.select(
    mode="fixed",
    candidates=dp_candidates,
    artifact=artifact,
)

# Scene-conditioned CAMP uses valid tokens from the same frozen DP encoder pass.
phi = masked_mean_scene_embedding(encoder_tokens, token_masks)
selected_scene_trajectory, scene_result = pipeline.select(
    mode="scene",
    candidates=dp_candidates,
    artifact=artifact,
    scene_embedding=phi,
)
```

Both calls return an unchanged copy of the selected DP trajectory together with
its selected row, candidate scores, active weights, active atoms, and status
pattern. The offline preference labels and actual-future trajectories are never
read by this inference interface.

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

## Installation

CAMP requires Python 3.9 or newer. For the core package and the included
reranker:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ./camp_core
```

Install the nuPlan geometry dependencies when rebuilding DP atoms:

```bash
pip install -e "./camp_core[nuplan]"
```

The full Trajectron++ experiment stack retains its older dependency set. Follow
[`adaptive-prediction/README.md`](adaptive-prediction/README.md) and install the
root [`requirements.txt`](requirements.txt) only when reproducing that path or
the full training environment.

## Tests

The deployable reranker and sparse endpoint schema can be checked with:

```bash
cd camp_core
python -m pytest \
  tests/test_diffusion_planner_v26_camp_reranker.py \
  tests/test_diffusion_planner_v26_sparse_schema.py
```

## License

This repository is released under the [MIT License](LICENSE).
