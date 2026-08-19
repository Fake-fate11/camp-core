# CAMP reranking for Diffusion Planner

`CAMPDPRerankingPipeline` loads the final K=8 CAMP weights and returns one
unchanged Diffusion Planner candidate. It supports both paper models:

- `fixed`: Fixed-weight CAMP, with one learned weight vector per endpoint-status pattern.
- `scene`: Scene-conditioned CAMP, with weights affine in the frozen DP encoder's
  256-dimensional masked-token mean.

Inference never computes the training Teacher and never reads logged or
simulated future actors. The online path is:

1. Diffusion Planner generates its ordered eight-candidate pool.
2. The existing online materializer computes the 16 deployment atoms and their
   endpoint statuses from current map, signal, prediction, and previous-plan inputs.
3. CAMP normalizes each observed atom as `clip(raw / train_scale, 0, 10)`.
4. The selected row is `argmin_k x_k^T w`; ties keep the lowest original row.

## Deployment bundle

The checked-in 50k bundle is under `artifacts/camp_v26_k8_50k/`:

```text
atom_scales.json
fixed_weight_camp.npz
scene_conditioned_camp.npz
fixed_weight_camp.json
scene_conditioned_camp.json
metadata.json
```

The two NPZ files are below 1 MiB in total. The frozen Diffusion Planner model
weights are not duplicated in this bundle; the scene mode reuses the DP model
already loaded by the planner.

## Minimal use

```python
from camp_core.integrations.diffusion_planner_v26_camp_reranker import (
    CAMPDPRerankingPipeline,
    build_camp_atom_artifact,
    masked_mean_scene_embedding,
)

pipeline = CAMPDPRerankingPipeline.from_directory(
    "artifacts/camp_v26_k8_50k"
)

# Each observed entry in `candidate_atom_values` is an eight-value vector.
# Missing and not-applicable endpoints remain statuses and receive no values.
candidate_atom_artifact = build_camp_atom_artifact(
    candidate_atom_values,
    endpoint_status,
)
selected_trajectory, fixed_result = pipeline.select(
    mode="fixed",
    candidates=dp_candidates,
    artifact=candidate_atom_artifact,
)

# For scene-conditioned CAMP, pool only valid tokens from the same frozen DP
# encoder pass. `token_masks` uses the encoder's ten token-type masks.
phi = masked_mean_scene_embedding(encoder_tokens, token_masks)
selected_trajectory, scene_result = pipeline.select(
    mode="scene",
    candidates=dp_candidates,
    artifact=candidate_atom_artifact,
    scene_embedding=phi,
)
```

`CAMPRerankResult` exposes the selected row, candidate scores, active weights,
atom names, endpoint-status pattern, and normalized atom matrix. The returned
trajectory is a copy of the original selected candidate; CAMP does not modify
candidate geometry or timing.
