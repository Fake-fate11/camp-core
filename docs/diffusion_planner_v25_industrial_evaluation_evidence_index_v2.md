# V25 Industrial Evaluation Amendment v2 Evidence Index

This index binds the corrected zero-model/zero-outcome contract. v1 remains a
superseded pre-correction diagnostic.

## Authority and implementation

- High authority SHA256:
  `720e9293f88de92b08bbfab39100baf46b396ca59a5b1c9a089cde5af0bfeca5`
- base/current v1 pointer:
  `f6b7ee2e18387341c0b13f5695a540568c70cfca`
- v2 implementation:
  `e226c1add02ff45a18008e808957adc316353bf3`
- fixed DP:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`

## Accepted v2 artifacts

| Artifact | Exact path | Root |
|---|---|---|
| contract | `/root/autodl-tmp/camp_dp_v25_industrial_evaluation_contract_v2_e226c1ad_720e9293` | `663977da1d1fe5d594764478881729f10483d13453c22024329375954b9ba3bb` |
| independent contract review | `/root/autodl-tmp/camp_dp_v25_industrial_evaluation_contract_v2_review_e226c1ad_720e9293` | `8ed937f521beb0f2163366b6999c8238eef173cdab67df7e5922e0f301a5b5f7` |
| scalar-leaf capability audit | `/root/autodl-tmp/camp_dp_v25_industrial_evaluation_capability_matrix_v2_e226c1ad_720e9293` | `86ab14e231129da7ec72dd7d632dd05336e03772c4af83e3d8e2dbdaec3e3afe` |
| independent capability review | `/root/autodl-tmp/camp_dp_v25_industrial_evaluation_capability_matrix_v2_review_e226c1ad_720e9293` | `0c6f25de790a48fb71001e94be31f0f56c92eb2c5f86c31fedc727f0a0b921cd` |
| implementation focused | `/root/autodl-tmp/camp_dp_v25_industrial_evaluation_focused_v2_e226c1ad_720e9293` | `0bccb1326860e3c1f74c5012fc6e40160722817a308212c8ec10f75b5209e4ec` |

Focused result: `123/123`; model/pool/selector and all scientific run counts
are zero; outcome reads and old artifact/CAS writes are zero.

## Exact sealed source inventories

Every reconstructable leaf binds exact sealed roots and exact inventory
entries, never `runs/*`:

- B4 execution root `e1bc886b...9881`, including exact
  `artifact_report.json` and `report.json` SHA256 entries;
- execution review root `f0afc12a...d98d`;
- Evaluation v2 contract/review roots `99501763...15e0` /
  `a7ba6866...fac0`;
- Evaluation v2 materialization/review roots `4fffc63b...4941` /
  `e1df26f7...27b`;
- metric-semantics contract/review roots `318e85f9...a758` /
  `fc04fd6e...ea95`.

The producer and separate-role reviewer independently verify complete seals,
the selected `SHA256SUMS` entries, exact JSON pointers, leaf applicability and
classification. Outcome materialization values are not opened.

## Registry and decisions

- parent/family rows: 56;
- exact scalar leaves: 161;
- reconstructable/missing/inapplicable: 119 / 41 / 1;
- hard-safety/guardrail/descriptive/not-testable: 14 / 96 / 9 / 42;
- familywise method:
  `holm_bonferroni_step_down_within_exact_family`, alpha `0.05`;
- hard safety and guardrails: layered intersection-union all-pass;
- current claim gate: false because numeric margins are not prospectively
  authorized;
- weighted compensation: forbidden.

## Superseded v1 evidence

The v1 contract/review/matrix/review/focused roots
`2e04cbfd...b31e`, `9d82089a...335a`, `7736d35f...9d31`,
`6d252bd2...136a`, and `0902230a...26d2`, plus the v1 final-docs
`140/140` root `704ec35b...e86`, remain immutable superseded
pre-correction diagnostics.

The initial v2 implementation roots
`2981e632...d2c8` and `c9b79252...3efc` are preserved as a
pre-capability inventory-SHA fixture diagnostic; no capability artifact was
formed under that implementation.
