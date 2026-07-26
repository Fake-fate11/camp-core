# V25 Sequential Latent Source-Audit Evidence Index

Date: 2026-07-26 (Asia/Shanghai)

## Current classification

`latent_input_rows_repeated`

This is a bounded source/preimage result for
`development_calibration:000 / sequential_batch1_x8 / repeat0`. It is not a
batch-8 runtime conclusion, a general model failure, OOD evidence, or a
retraining decision.

## Authority

- High authority:
  `f9a91cbeac8f004cbac8b87bf170e51d54a1a09f5bc25fb256c3abd9e5106ba4`
- pointer authority:
  `c1c4a19a5d3e93605fb46f1a4fe529fac3458f8d`
- implementation:
  `c33767307148e23397eaab28eae4c501ddadda29`
- fixed DP:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`

## Sealed roots

| Role | Exact directory | Root SHA256 |
|---|---|---|
| contract | `/root/autodl-tmp/camp_dp_v25_sequential_latent_source_audit_contract_c3376730_f9a91cbe` | `34c49c2b5378475fce133d7e6a7e2353f3b9a6f864bc18777c015bcfa4e5812f` |
| contract review | `/root/autodl-tmp/camp_dp_v25_sequential_latent_source_audit_contract_review_c3376730_f9a91cbe` | `4c06f34630c9f979ae35eb735b8ba0de648fdddac99e4b853e83d3e20013b531` |
| focused | `/root/autodl-tmp/camp_dp_v25_sequential_latent_source_audit_focused_c3376730_f9a91cbe` | `19baef92203fa39f589ab00a24f6363f933121eb671c81f4cc0a5bd98a5e0c07` |
| audit | `/root/autodl-tmp/camp_dp_v25_sequential_latent_source_audit_c3376730_f9a91cbe` | `ef7fed1d077aa2edcdfe4114daaf1904b936ead23d713fc4ba96acbcb8cedc3e` |
| audit review | `/root/autodl-tmp/camp_dp_v25_sequential_latent_source_audit_review_c3376730_f9a91cbe` | `bd81175f3088755e41f799854bcc84d09deca8da1e443b1e20ad7cbd3dd09ef6` |

Each artifact has a complete seal and `run.exit=0`. Focused tests are 14/14.

## Exact preimages and bindings

- requested latent tensor:
  `b995f83f083df0321b8a575e10065aac041c14c30830129963048b73b7ebfea0`
- latent row cardinality: `2/8`
- latent duplicate group: `[[1,2,3,4,5,6,7]]`
- candidate tensor:
  `e3ebd9e0de7cad13d92b9479a0c2ed6286fb48e0649b103b249e163ef3598d84`
- neighbor tensor:
  `03a26f6dcd94f304d01e97a5deaae3fa9d1b85c3498b11efdf84b87f6269b860`
- precondition receipt:
  `d97fc4bbcfdb1ccf8fed517b8c47b89e7401952b1a9b5b5f1766ae50f38f3a45`
- row-to-call-to-forward-to-output bindings: `8/8`

## Independent reconstruction

The reviewer does not import the producer audit/dataflow oracle. It separately:

- reconstructs PCG64 seed 61000 latent bytes;
- applies the literal seven-row broadcast;
- verifies source SHA and AST spans for four files;
- decodes candidate and neighbor bytes;
- rebuilds all eight forward IDs and output-row bindings;
- selects the same mutually exclusive taxonomy.

Mutation tests fail closed for latent construction, overwrite, row index,
forward/output binding, fixed-DP consumption, missing receipt, authority, and
taxonomy changes.

## Boundary

The existing latent policy is not modified. The minimum independent-rows fix
is proposal-only and would require a new versioned policy contract before any
model execution. Calibration 0/640, threshold, validation, closed-loop,
Fresh/holdout, training/retraining, raw outcome reads, old artifact/CAS writes,
and claims all remain zero/false.
