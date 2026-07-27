# V25 Industrial-v3 Multiroute Review-only Recovery Report

## Outcome

The immutable 100-cluster, 300-arm, 19,200-tick nonholdout execution and the
corrected industrial-v3 evaluation now have a complete external authority
chain and a separate-role independent review. The accepted status is
`accepted_exploratory_multiroute_nonholdout_evaluation_via_external_complete_authority_chain`.
No producer, evaluator, model, execution, pool, selector, Fresh, or training
run was repeated.

This is an exploratory development/nonholdout result. It is not a Fresh or
confirmatory claim, industrial certification, deployment decision, or evidence
that retraining is unnecessary.

## Immutable scientific inputs

- execution root:
  `7d143a95cf42aa702e362dd75a1b8c5d7559690bdcd701a001ee0fac186fb052`
- execution-review root:
  `6c90f5e966e78203702c71168098ae3fe93f385e7af750890e248ef156cabf27`
- corrected evaluation root:
  `16a156ac21fba0cd5038802df7b0735f4c66d25b1cb73663fd8710fda97cdf8c`
- authorized preflight root:
  `5f56246ac312682920f0aaae63cab3d5f4f0ea5e75c85156b30395ce8e30f341`
- denominator: 100 independent prespecified clusters, 300 arm-runs, and
  19,200 retained ticks
- execution accounting: 19,200 complete, 0 failed, 0 unattempted, 19,200
  formal model calls, and 0 hard-integrity failures

The corrected evaluation itself remains immutable. The recovery reviewer
consumed its sealed bytes plus the sealed execution and independently rebuilt
all 100 x 161 x 3 cluster/leaf/arm values.

## External authority and independent review

- merged authority:
  `181be7266035f4a1a40c11bf1bf1c3458dd79491e97e5e91ecd1914cbc7672b4`
- stage-authority root:
  `1015df19895128a46f6b7717974d8a7aed51b9d96174f89724aa74ab4f987963`
- stage-authority-review root:
  `eacad2d58275ac65f9ad3e0e7f45abe5d20e9fd48e383fd0f3650d3292b8ab9a`
- stage-authority orchestration root:
  `417d44a67bd5ad522a26a00e1a12e131b8a3d71baf727435ef35d41882cf02b1`
- evaluation-review root:
  `e652394725a038d3b501ecdd30f9e39e9e26bc5cbd6d4b6c3789b16550af6fd3`
- review-only orchestration root:
  `1a92d1fd1c892679335e23823b7ed6df849bd32d053b8ff045decc7144e8dbb5`
- orchestration-focused root:
  `6677cb361dac75d8d2cd55ce1c43b740717f75cb2913770c250a60409efb9c7c`

The tracked orchestrator stored producer/reviewer stdout, stderr, and exit
codes separately, propagated the first real nonzero exit, wrote machine JSON
and canonical one-line root receipts, and used verified seals rather than
stdout parsing. Review-only mode recorded
`producer_skipped_reuse_sealed=true`.

## Industrial-v3 descriptive vector

All 161 scalar leaves remain present:

- 100 `computed_exploratory_multiroute`
- 57 `evidence_missing_or_mixed_applicability`
- 4 `scientifically_inapplicable`

For each selector arm, 87 leaf comparisons have complete 100-cluster
descriptive summaries and 74 retain full-denominator missing/failure status.
Using each leaf's frozen direction, the signs of the descriptive oriented mean
delta versus candidate0 are:

| Arm | Positive | Exact zero | Negative | Missing/not evaluable |
| --- | ---: | ---: | ---: | ---: |
| Static14D | 45 | 8 | 34 | 74 |
| Scene14D | 49 | 7 | 31 | 74 |

These counts are descriptive only and do not aggregate into a score. Ordinary
paired Student-t 95% intervals remain descriptive. Holm, IUT, NI, benefit, and
claim gates remain not evaluable because prespecified numeric margins are not
authorized. SafetyCost remains an immutable legacy exploratory diagnostic and
was not computed here.

## Verification

The focused set passed 20/20 tests on the authorized AutoDL Python 3.12.3
runtime. It covered the tracked orchestration exit topology, canonical machine
root/receipt linkage, critical root/HEAD/continuation/exact-directory
mutations, and the actor-binding review path. The full suite and the previous
34-test actor-binding suite were intentionally not repeated.

## Claim boundary

The package accepts only an exploratory multiroute nonholdout evaluation
through a complete external authority chain. It does not establish causal
benefit, general OOD support, industrial or real-road safety, ISO/SAE
conformity, production readiness, promotion, deployment, or no-retraining.
