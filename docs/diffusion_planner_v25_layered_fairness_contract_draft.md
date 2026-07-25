# V25 Layered Fairness Contract Draft

Status: outcome-independent draft; no closed-loop or Fresh execution authority.

## Layer 1: state-matched offline selector replay

- Freeze one ego observation/state and its complete model input fingerprint.
- Invoke the versioned pool generator once to create one same-ego K=8 tensor.
- Freeze model/checkpoint, latent tensor, input SHA, invocation ID, tensor SHA,
  pool ID, row order, dtype, shape, and finiteness.
- Pool baseline uses the prospectively declared row0 rule unless another rule
  is separately preregistered before outcomes.
- Static14D and Scene14D may only compute atoms/context/weights/scores and
  select a row from that immutable tensor.
- From pool freeze through selection, model calls, latent replacement, and
  trajectory generation must each remain exactly zero.
- This layer isolates selector behavior; it is not closed-loop performance.

## Layer 2: compute-matched closed-loop

- Each arm receives the same versioned pool-generator contract, checkpoint,
  K=8 candidate budget, latent policy, numerical policy, and compute budget.
- At each arm's own current ego state, one model invocation generates that
  arm's candidate pool before selection.
- The baseline pays the same pool-generation cost as CAMP arms.
- State divergence is expected after different selections. Consequently,
  candidate tensors across arms/ticks are not required or permitted to be
  described as identical after divergence.
- Pool generation and selection must remain separate machine roles with
  separate call counters and provenance.

## Latency accounting

Report pool-generation latency separately from atom, context, weight, and
selector latency. Report their sum as total only when stage denominators and
opportunities match. The baseline includes pool cost and may mark uncalled
CAMP-only stages as n/a, never zero-cost evidence.

## Future scientific contract

Endpoints, thresholds, NI margins, multiplicity, missing-data handling,
cluster inference, hard gates, and claim language require a new prospective
nonholdout contract before any confirmatory execution. The historical B4 and
Evaluation v2 results cannot select those rules or authorize a new claim.

No Fresh, closed-loop execution, training, promotion, deployment, or online
activation is authorized by this draft.
