# V25 Batch8-Only Calibration Contract Design Report

## Outcome

The outcome-independent contract design and its separate-role literal review
passed. This package does **not** authorize or execute calibration acquisition,
threshold materialization, validation, closed loop, Fresh/holdout, training, or
retraining.

The only formal generator mode is
`new_single_invocation_batched_k8_candidate_pool`. Each planned run contains
one same-ego model invocation with expanded batch `B=8`. The historical
`sequential_batch1_x8` path remains an immutable, non-gating diagnostic and
contributes zero denominator, numeric keys, thresholds, hard gates, or primary
latency.

## Authority and immutable inputs

- High authority SHA256:
  `81dbf890717297cebf477ee9192c98c5c4f641bd3b976cab5154d6da872a5f7b`
- implementation HEAD:
  `383d9944ac1bc912880d15ef3c5ed4944c07c9ed`
- fixed-DP HEAD:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- accepted batch8-primary contract/review roots:
  `15cf642f5abcb1cd44687e8f4298517f47e8c878633602e9b42fcffe7c30e5d7` /
  `a0cd179311b5ce1fd18b7e764154d92041bfda57216c0be2365aa20100133978`
- accepted one-state batch8 diagnostic/review roots:
  `6a9e1a364b6d25716a471d34039553b11521c2d911563df0e3ee0edf1ed3eec5` /
  `92e33a3e1747764a65d6d6b8e38645f7faa9825b2b08c980255025ac840073c3`
- preserved v5 contract/review roots:
  `78584ecc74a1a4f42e18fe0f4ee81e4fd0f48e98e33fd56c7128954c2ce0e4c6` /
  `3e0f5c5247fc3fc4e877d0c2597022a5b31c2e297023fd39cc0a58060c0491e5`

All legacy Fresh B4, corrected-evaluation, Evaluation v2, scientific CAS, and
continuation CAS artifacts remain unchanged.

## Exact future denominator

The design freezes:

- 64 development-calibration states;
- five repeats per state;
- one formal batch8 invocation per repeat;
- 320 planned model invocations;
- ten unordered repeat pairs per state;
- 640 within-mode pair receipts;
- 320 Static14D and 320 Scene14D real-selector receipts, 640 total;
- `state` as the only independent statistical unit.

Rows and ticks are state-internal observations. Every planned slot and pair is
retained. Dropping, replacement, complete-case shrinkage, sequential receipts,
and cross-mode receipts are forbidden.

## Numeric registry and threshold math

The sole phase is `batch8_within`. Its registry contains exactly the 22 former
v5 within-mode endpoints:

- 14 training-scale-normalized atom deltas;
- ego position, heading, and speed trajectory deltas;
- neighbor position, heading, and speed trajectory deltas after exact actor-slot
  matching;
- Static14D and Scene14D maximum shared-eligible absolute score deltas.

No cross-mode normalized score, margin-ratio, rank-error, neighbor-inflation,
sequential, or old 73-key projection is present.

Each state uses the higher empirical q99 over its ten unordered repeat-pair
errors: `sorted_values[ceil(0.99*(10-1))] = sorted_values[9]`. Across the 64
state values, the contract freezes 10,000 with-replacement bootstrap samples
from `numpy.random.Generator(PCG64DXSM(825071))`; each sample uses its index-63
higher q99, and the 95% upper value is sorted bootstrap index 9500. The future
threshold is the maximum of that value and the endpoint-specific resolution
floor. Equality passes (`error <= threshold`); nonfinite or missing evidence is
retained and fails closed. Threshold materialization is not authorized here.

## Hard gates

Every future raw run must independently prove:

- one formal model call, one ego state, same-ego expanded `B=8`;
- eight unique finite prefrozen latent rows;
- finite candidate and neighbor tensors and eight unique candidate rows;
- exact input/state/model/checkpoint/source/runtime fingerprints;
- candidate-tensor immutability;
- post-pool model, DP, latent-generation, and candidate-generation calls all
  equal zero;
- nonempty Static14D and Scene14D masks and selected actions bound to the same
  frozen pool/tensor.

Any failure is retained and makes qualification fail closed. Failure classes
are separated into runtime instability, selector functional failure, training
support gap, and authority failure.

## Training-support audit

The accepted training root
`8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9`
and `runtime_atom_scales.json` SHA
`72694a5f21c0f99d6506ed078b53e75c76f26319005e9a0dd7cbc30ca7f688eb`
uniquely support the 14 atom normalization scales. The current authority does
not bind a sealed same-ego batch8 training candidate distribution or
Static14D/Scene14D training score, mask, margin, eligible-count, and selected
action distribution with an independent review.

The training-support status is therefore
`evidence_missing_prespecified_training_support_reference`. This is a
fail-closed evidence boundary, not a retraining result.

Before any future acquisition authority, a separate sealed training-support
audit must derive its reference exclusively from training artifacts. The
contract freezes 20 fields (14 normalized atoms plus Static/Scene scores,
margins, and eligible counts), empirical 0.5%/99.5% inclusive reference
intervals, at least 1,000 finite training samples per field, 40 row
observations per calibration state, minimum inclusive per-state coverage 0.95,
at least 61 of 64 passing states, and all-20 multiplicity without a weighted
total. Calibration or validation outcomes may not set or alter those
references.

No “training adaptation passed” or “retraining unnecessary” conclusion is
authorized.

## Independent review and tests

The reviewer imports no producer threshold, endpoint, decision, selector, pool,
or model oracle. It locally reconstructs:

- the 320/640/640 topology;
- the exact 22 formulas, units, applicability, floors, and missing rules;
- q99 and PCG64DXSM bootstrap/UCB mathematics;
- the training-scale binding and missing training-support reference;
- hard gates, failure retention, and sequential/cross exclusion.

The authoritative AutoDL focused artifact ran 84 tests. Adversarial coverage
includes reintroducing sequential/cross modes, replacing 320 with the old 640
denominator, using 73 keys, treating row/tick as the statistical unit, dropping
failures, using eight model calls as one, and allowing calibration values to
set training-support thresholds.

## Sealed roots and mechanical diagnostic

- contract root:
  `f4216e9e59d7cc81cf8d7ebd69e0bdd38b1399ec11d6fe95866994b309d53c1c`
- independent contract-review root:
  `8f2b198be18ef01607f4e355e014f3de07f049981ee05c0c18b96017b9237457`
- AutoDL 84-test focused root:
  `ec272560f2bb7c31a32cea8e9e5f6d83caad4f041ae5340a3f4881f8db90bdd5`

The earlier d6 contract root
`2e93f633ec6053200b5bdc32ff2500118ee059db0e8be1415ed7c76b9f2b37a4`
is preserved as a superseded mechanical diagnostic. Its reviewer failed before
artifact creation because canonical JSON key sorting changed mapping insertion
order. The repaired reviewer requires the same exact keysets and values without
using insertion order as semantic authority.

## Scientific boundary

This package establishes an executable, outcome-independent design only.
Actual model/pool/selector/calibration calls are zero. It provides no benefit,
general OOD, no-retraining, Fresh, industrial safety, promotion, deployment,
online activation, or production-readiness claim. The legacy scientific result
remains `honest_no_claim_under_frozen_preregistered_all_gate`.
