# V25 Industrial Evaluation Amendment v3 Evidence Index

## Live v3 implementation

| Evidence | Root / value |
|---|---|
| Implementation HEAD | `c197c1e5c9b8ce1aa17d1b85825c95a5e7237f64` |
| High authority | `720e9293f88de92b08bbfab39100baf46b396ca59a5b1c9a089cde5af0bfeca5` |
| Fixed DP HEAD | `7a1d33da277a1992ec474b5383a0c963c72e04e4` |
| Contract root | `908fe1d57014e4932f71462d6d7e73ec58390f3296b3018df38092e4c0b128cb` |
| Independent contract-review root | `23bb07ac537f9d53f7a2860b2314f55da4e2d468590d002c6cf25733f5e48556` |
| Capability-matrix root | `fbcc8ab194520534c3b4986cccaf3d9a073b2cf975b6e3f006f61abe7791f20d` |
| Independent matrix-review root | `f32cb19b2c7bbd64e290f07a270f3e43462d31c86dc130a0c23a8b6eb363eec3` |
| Authoritative implementation focused root | `06f221f4cf8fc86ae19f632fcc2fa74080575966224090fc552db89a190abb5b` |
| Focused tests | `135/135` |
| Contract canonical SHA256 | `d8c7ca0ed4e59b6e3887e78cf1dea4116a1cd863ea5bed061a8e7f3afb1177db` |
| Capability canonical SHA256 | `e3bb1c34e0a89b5d1dee234de88f346b545c962a1a3af1fac4dfbb8a5941deb2` |

Exact directories use the immutable tag `c197c1e5_720e9293`:

- `/root/autodl-tmp/camp_dp_v25_industrial_evaluation_contract_v3_c197c1e5_720e9293`
- `/root/autodl-tmp/camp_dp_v25_industrial_evaluation_contract_v3_review_c197c1e5_720e9293`
- `/root/autodl-tmp/camp_dp_v25_industrial_evaluation_capability_matrix_v3_c197c1e5_720e9293`
- `/root/autodl-tmp/camp_dp_v25_industrial_evaluation_capability_matrix_v3_review_c197c1e5_720e9293`
- `/root/autodl-tmp/camp_dp_v25_industrial_evaluation_focused_v3_c197c1e5_720e9293`

## Exact topology

| Dimension | Count |
|---|---:|
| Parent endpoints | 56 |
| Scalar leaves | 161 |
| Noninferiority | 110 |
| Descriptive-only | 9 |
| Not testable | 42 |
| Hard safety | 14 |
| Guardrail | 96 |
| Reconstructable with frozen transform | 119 |
| Evidence missing | 41 |
| Scientifically inapplicable | 1 |

Exact test-family membership:

| Family | Leaves |
|---|---:|
| hard_safety_collision | 4 |
| hard_safety_red | 3 |
| hard_safety_containment_direction | 7 |
| safety_dynamic_exposure_guardrails | 40 |
| operations_guardrails | 20 |
| planar_kinematic_proxy_guardrails | 36 |
| descriptive_only_not_tested | 9 |
| not_testable | 42 |

## Superseded diagnostics preserved

v2 remains a sealed pre-final diagnostic:

- contract `663977da1d1fe5d594764478881729f10483d13453c22024329375954b9ba3bb`;
- review `8ed937f521beb0f2163366b6999c8238eef173cdab67df7e5922e0f301a5b5f7`;
- matrix `86ab14e231129da7ec72dd7d632dd05336e03772c4af83e3d8e2dbdaec3e3afe`;
- matrix review `0c6f25de790a48fb71001e94be31f0f56c92eb2c5f86c31fedc727f0a0b921cd`;
- focused `0bccb1326860e3c1f74c5012fc6e40160722817a308212c8ec10f75b5209e4ec`;
- final docs `16162cac21ddbe060eae6bdc035d34c34fb78494133da5122fbe7d82bffb559b`.

The earlier v1 roots and the pre-capability inventory-SHA fixture diagnostics
remain in the historical v2 index: `2e04cbfd...b31e`,
`9d82089a...335a`, `7736d35f...9d31`, `6d252bd2...136a`,
`0902230a...26d2`, `2981e632...d2c8`, and `c9b79252...3efc`.
None is overwritten or represented as the current authority.

## Zero-run and claim boundary

`model/pool/selector=0`,
`training/calibration/validation/closed-loop/Fresh/holdout=0`,
`outcome_values_read=false`, `old_artifact_or_cas_write_count=0`,
`claim_authorized=false`.
