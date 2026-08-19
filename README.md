# CAMP Core: Corrective Adaptation for Motion Prediction

CAMP is a post-hoc decision layer that reranks trajectories from a frozen
prediction or planning model. It changes neither the upstream generator nor the
candidate trajectories: it learns how to choose among the candidates already
available in each scene.

The original CAMP integration uses Trajectron++ prediction candidates. The
current primary integration applies the same idea to Diffusion Planner (DP),
whose candidates already encode interactions among the ego vehicle, agents,
and map. CAMP therefore operates only at the final decision layer.

## Method overview

For scene $i$, the frozen generator returns an ordered pool
$\{\tau_{ik}\}_{k=1}^{K}$. CAMP computes a lower-is-better score from
deployment-available candidate atoms $x_{ik}$:

- **Fixed-weight CAMP:** $s_{ik}=x_{ik}^{\mathsf T}b_{p(i)}$.
- **Scene-conditioned CAMP:**
  $s_{ik}=x_{ik}^{\mathsf T}\Theta_{p(i)}[\bar\phi_i;1]$.

Here, $p(i)$ is the endpoint-status pattern and $\bar\phi_i$ is a pooled
representation from the frozen DP encoder. The selected trajectory is
$\arg\min_k s_{ik}$, with ties resolved by the original candidate order.

Training uses logged outcomes only to construct offline preference targets.
Those targets favor safety first, then comfort and the remaining driving
qualities. The online score itself uses only information available at decision
time. CAMP minimizes a target-set ranking hinge under CVaR tail risk with
quadratic regularization; finite-candidate separation supplies the Benders
cuts. The fixed generator, candidate identities, atom definitions, and online
inference inputs remain unchanged throughout training.

## Current Diffusion Planner configuration

The checked-in deployment bundle is the completed B/P 50k, K=8 configuration:

- eight ordered DP candidates, with `candidate0` equal to `row0`;
- 16 candidate-level decision atoms covering safety, rules, progress, comfort,
  and previous-plan continuity;
- 24 endpoint-status patterns;
- endpoint-local `observed`, `not_applicable`, and `typed_missing` states;
- no zero filling for unavailable endpoints;
- fixed-weight and scene-conditioned CAMP checkpoints;
- raw affine scoring without an inference-time Teacher.

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

## Training and evaluation flow

1. Run the frozen generator once to create an ordered candidate pool.
2. Materialize the deployment atoms and endpoint states for every candidate.
3. Use logged outcomes offline to build preference targets and ranking margins.
4. Train fixed-weight CAMP; train scene-conditioned CAMP with the frozen encoder
   representation when that comparison is required.
5. Evaluate the selected existing trajectories with paired metrics. Safety,
   comfort, progress, displacement error, feasibility, continuity, and latency
   remain separate result families.
6. Deploy only the learned decision weights and atom scales. The Teacher and
   logged futures are excluded from online selection.

This separation is central to CAMP: privileged outcomes supervise the decision
rule during training, while deployment uses only observable candidate and scene
features.

## Repository layout

- [`camp_core/`](camp_core/): CAMP atoms, scoring models, optimization code, and
  the deployable DP reranker.
- [`artifacts/camp_v26_k8_50k/`](artifacts/camp_v26_k8_50k/): compact final K=8
  deployment parameters.
- [`scripts/`](scripts/): experiment materialization, training, and evaluation
  programs.
- [`docs/`](docs/): method, integration, and experiment notes.
- [`adaptive-prediction/`](adaptive-prediction/): the original Trajectron++ and
  trajdata integration used by the earlier CAMP experiments.

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
python -m pytest \
  camp_core/tests/test_diffusion_planner_v26_camp_reranker.py \
  camp_core/tests/test_diffusion_planner_v26_sparse_schema.py
```

## License

This repository is released under the [MIT License](LICENSE).
