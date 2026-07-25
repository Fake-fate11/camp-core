# V25 Target-Architecture Development Qualification

Date: 2026-07-25 (Asia/Shanghai)

## Outcome

The fixed Diffusion Planner supports a new development/nonholdout capability:
one actual `Diffusion_Planner.forward(inputs)` invocation can consume eight
copies of the same ego observation/state with eight frozen latent rows and
produce a same-ego K=8 candidate tensor. This is a capability qualification,
not a closed-loop experiment, Fresh rerun, training result, or scientific
effect claim.

The operational launch remains pinned to `batch_size=1`. Therefore this result
does not claim that the previous operational default already generated K=8 in
one invocation.

## Superseding architecture classification

The sealed B4 intervention is preserved unchanged and is now classified as
`compute_augmented_candidate_expansion_plus_reranking`: candidate0 came from
the original model call and rows 1-7 came from seven additional sequential
model calls before CAMP reranking. It does not demonstrate reranking of an
unchanged, already-available same-invocation K=8 pool.

All B4 execution, execution-review, corrected-evaluation, Evaluation v2,
scientific ledger, continuation CAS, endpoint values, and the legacy decision
`honest_no_claim_under_frozen_preregistered_all_gate` remain immutable.

## Sealed authority

- Architecture amendment:
  `/root/autodl-tmp/camp_dp_v25_target_architecture_amendment_2cf030a6_8680c1b19ce0620b`
  (`3cfba03b2fd21cfa068610f8989f0c2b1df890cf64f6b1ac4b10eae67e291c7b`)
- Independent amendment review:
  `/root/autodl-tmp/camp_dp_v25_target_architecture_amendment_review_2cf030a6_8680c1b19ce0620b`
  (`202461e5045bba42cb10ad7bbdb03c36b82c00defce2df60edd6a971d1d2fd8f`)
- Capability artifact:
  `/root/autodl-tmp/camp_dp_v25_same_ego_k8_capability_2cf030a6_8680c1b19ce0620b`
  (`fa94808c70ce1953d50b52497f9c4d056dabccd96e3ffdaed84faead5f2ed8e6`)
- Independent capability review:
  `/root/autodl-tmp/camp_dp_v25_same_ego_k8_capability_review_303dbb71_8680c1b19ce0620b`
  (`cb9f4efd5d72962513ea83777a68f3ffa5455fd731bc1cc5859b407cd9d25ac1`)
- Authoritative implementation focused suite:
  `/root/autodl-tmp/camp_dp_v25_target_architecture_qualification_focused_303dbb71_8680c1b19ce0620b`
  (`47c099f78986b21f0fb116d1989d41fdc96a001859a4e14a860e94f33b533ba1`);
  52 passed, 2 skipped.

The first capability artifact
`5833ba72726a0e7d0a55aa4659ae800991f029d284e730df6afee7f9fb18a967`
is retained as a superseded engineering diagnostic: its latent preimage was
captured after the model mutated a working tensor, and no independent review
artifact was formed.

## Fixed-model provenance

- Fixed-DP HEAD:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Checkpoint SHA-256:
  `4ffaeea21cd29904da73349eea642e1d28f8ddbf02be363b7386e3a9b8ebcc75`
- Model source SHA-256:
  `341c8f5798cae83fdee3ae7203243ab129458d8eab362e0c3a1c7daee08d502d`
- Decoder source SHA-256:
  `8e81d1e9aa879dd0c0762d623dbe7480786e2618ccb261d10fd72cc00192e7dd`
- Encoder source SHA-256:
  `360b3632cc0f9d65ffb25ed4adc906b498d824df0d4b6e37f5c59eb252f8daab`
- Formal entry point: `Diffusion_Planner.forward(inputs)`
- Source and checkpoint modified: `false`

## Same-ego K=8 capability

The input was one development/nonholdout v24 source-only record. No Fresh or
holdout source was accessed and no simulator step advanced.

- Source input SHA-256:
  `0bebc11643a8b6cf3b42cca34ff774eff5d77927339fd276efdd9f60af42ff17`
- State SHA-256:
  `ccb52028b49d73fede25b3ec3c3b7fb9d848759383628068c84c761d078fabfe`
- Route SHA-256:
  `63890f60cb662a78ea733576397c3b91e942f854bd5ca92007e6449dbf4f24bd`
- Source batch: 1 ego; expanded model batch: 8
- Candidate-axis semantics: `same_ego_candidate_batch`
- Agent-as-ego batch: `false`
- All nonlatent input rows identical: `true`
- Frozen latent: seed 24001, noise scale 1.0, shape `[8,321,81,4]`,
  `float32`, finite, row0 zero
- Latent SHA-256:
  `9f40a00d7456c1aed377398d15ffe146116b9883154bfe88b7a45e0cb34bdd5a`
- Temperature: not exposed by the fixed-DP formal interface

The primary pool used exactly one model call:

- Invocation ID:
  `22b8cec0cb500e2c6cfb6c0ce96a3d483991b3241716a8f21b65bd59ed062223`
- Model input SHA-256:
  `a6f524c6ca381ca89f915dc10f2fbd8427a952137b1dbc06f628670db1640832`
- Output: shape `[8,80,4]`, `float32`, all finite
- Candidate tensor SHA-256:
  `02685eb0edfd0eb89e358bd8d75a7e64465a60b280484cd6c767ab1a084d4d72`
- Pool ID:
  `975404af834e18b076a8e1a88c46fdff4ca2d1dfd50f9396907963bb02750e90`
- Unique row SHA count: 8
- Pairwise RMS range: 0.0556779690 to 1.0107800961

The repeat invocation was bitwise deterministic: tensor SHA matched and
maximum absolute error was 0. Global RNG state SHA was identical before and
after the controlled calls.

## Batch-versus-sequential relation and training decision

Eight batch-size-one calls using the same state and corresponding frozen
latent rows were compared row by row with the one-call batch-8 output.
All rows passed the outcome-independent `atol=1e-5`, `rtol=1e-5` contract.
The maximum absolute error was `3.814697265625e-05`; the eight row maxima were
`[2.288818359375e-05, 2.6702880859375e-05, 1.9073486328125e-05,
3.814697265625e-05, 2.86102294921875e-05, 3.24249267578125e-05,
3.4332275390625e-05, 2.86102294921875e-05]`.

The small non-bitwise differences are consistent with batched numerical
ordering under the frozen tolerance. No candidate-distribution drift was
identified by this qualification, so it does not supply evidence requiring
retraining. No training was executed, and this bounded result is not a general
OOD guarantee.

## Selector-after-pool machine gate

The pool-matched baseline, Static14D, and Scene14D structural receipts bind the
same pool ID, candidate tensor SHA, model/checkpoint, input SHA, and forward
invocation ID. After the pool was frozen:

- model/DP calls: 0
- latent replacements: 0
- trajectory generations: 0
- outcome values read: `false`

The structural probe selected row0 for every label under an explicitly frozen,
outcome-independent qualification rule. This proves pool binding and the
zero-call selector boundary only. It is not an execution of Static14D or
Scene14D scoring and supplies no comparative effect evidence.

## Fairness architecture

Two distinct future designs are frozen as a draft:

1. State-matched offline selector replay freezes one state and one K=8 tensor,
   then compares the pool baseline, Static14D, and Scene14D without any model
   call inside the selector.
2. Compute-matched closed-loop evaluation gives each arm the same versioned
   pool-generator contract and K=8 compute budget at its own branched state.
   Once states diverge, it must not claim identical tensors across arms/ticks.

Pool-generation latency is separate from atom, context, weight, and selector
latency, and the baseline bears the same pool-generation cost. Endpoints,
statistics, multiplicity, hard gates, and claims are not authorized here.

## Decision boundary

Qualification status:
`passed_development_nonholdout_same_ego_single_invocation_k8_capability`.

Next authority remains a scientific-contract decision before any implementation
or execution of a new closed-loop protocol. This package authorizes no Fresh,
holdout, training, claim update, promotion, deployment, online activation,
real-road safety statement, broad unseen-map statement, or native-ranked Top1
statement.
