# V25 Industrial-Oriented Evaluation Evidence Index

## Authority

- High authority SHA256:
  `720e9293f88de92b08bbfab39100baf46b396ca59a5b1c9a089cde5af0bfeca5`
- Base HEAD:
  `456aabb70308271f4b7b1dcb30550fe5574fc389`
- Implementation HEAD:
  `5316bb8cc37a0bdc539923991a07709dfd45b2ed`
- Fixed DP HEAD:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Claim authorized: `false`
- Model/pool/selector calls: `0`
- Outcome values read: `false`
- Old artifact/CAS writes: `0`

## New implementation

- Contract module:
  `camp_core/camp_core/integrations/diffusion_planner_v25_industrial_evaluation_contract.py`
- Separate-role reviewer:
  `camp_core/camp_core/integrations/diffusion_planner_v25_industrial_evaluation_review.py`
- Contract freezer:
  `scripts/integrations/freeze_diffusion_planner_v25_industrial_evaluation_contract.py`
- Contract reviewer:
  `scripts/integrations/review_diffusion_planner_v25_industrial_evaluation_contract.py`
- Capability producer:
  `scripts/integrations/materialize_diffusion_planner_v25_industrial_evaluation_capability_matrix.py`
- Capability reviewer:
  `scripts/integrations/review_diffusion_planner_v25_industrial_evaluation_capability_matrix.py`
- Adversarial tests:
  `camp_core/tests/test_diffusion_planner_v25_industrial_evaluation_contract.py`

## Sealed artifacts

These roots are filled from the authoritative AutoDL zero-model chain:

- Contract:
  `/root/autodl-tmp/camp_dp_v25_industrial_evaluation_contract_5316bb8c_720e9293`
- Contract root:
  `2e04cbfdd386ccb04a0efb0b818a1d481aea7ddfb3ad8ba580ecfbc0b91fb31e`
- Independent contract review:
  `/root/autodl-tmp/camp_dp_v25_industrial_evaluation_contract_review_5316bb8c_720e9293`
- Independent contract review root:
  `9d82089ad6ce3b41789662c0d232c33c45a86103d1cd5348da54b51d5516335a`
- Capability matrix:
  `/root/autodl-tmp/camp_dp_v25_industrial_evaluation_capability_matrix_5316bb8c_720e9293`
- Capability matrix root:
  `7736d35f5a33d47967b83ad3c5a236dd3d9e5d9d0d66450e8bf6dbe4109f9d31`
- Independent capability review:
  `/root/autodl-tmp/camp_dp_v25_industrial_evaluation_capability_matrix_review_5316bb8c_720e9293`
- Independent capability review root:
  `6d252bd2a52eb974e77234ab0ed85104f0dbc068f08bc5d08204bc2c1024136a`
- Implementation focused:
  `/root/autodl-tmp/camp_dp_v25_industrial_evaluation_focused_5316bb8c_720e9293`
- Implementation focused root:
  `0902230a0640622667c0fb79b1c9f8f069070010cf84abe894ac2e6f7afa26d2`
- Implementation focused test count:
  `102`

## Immutable accepted source bindings

- Fresh B4 execution:
  `e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881`
- Fresh B4 execution review:
  `f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d`
- Corrected evaluation:
  `4a817b4bbd17449486e3258c0d4b07102929d5f12d60fa4bb73056eb726afb9f`
- Corrected evaluation review:
  `94b048ace4a2a539532ccc64fe061afb51bc6b4e23ee2e5a5affd1fc2ef69459`
- Evaluation v2 contract:
  `99501763a4a88c9d80fff738054b37593717df0b6d33e3749ad451d9e52a15e0`
- Evaluation v2 contract review:
  `a7ba686647ccfe64f45a3304a00a392c1a362534833023fe26e0343a374bfac0`
- Evaluation v2 materialization:
  `4fffc63bbeef6c2f6c0f26d8fb8b5af2842ad6e8c998a0ed04342aff73134941`
- Evaluation v2 review:
  `e1df26f72402745aa68041a068b347b6fd1dad1abe9ed173baf05571c666427b`
- Metric-semantics contract:
  `318e85f9656a5dd79c9fb0ad6c1dfcd94678b35c4aba455f3909cf3475cca758`
- Metric-semantics contract review:
  `fc04fd6e45487df6c9bf5313b9ee6d633f91303e0a1aa00f0a3114b8134fea95`
- Metric-semantics amendment:
  `99fd5e571160a3ac3d5bb2b6d6f3391c3da5965bf592707ff85c88080ac2dbcf`
- Metric-semantics amendment review:
  `88b35ab8ef51807c848200675ceeebe6b26e15a4f4b34da51f131e9303f37898`

No immutable root or legacy value was modified.

## Registry and capability receipt

- Contract schema:
  `camp_dp_v25_industrial_oriented_evaluation_contract_v1`
- Capability schema:
  `camp_dp_v25_industrial_oriented_evaluation_capability_matrix_v1`
- Endpoint count:
  `56`
- Domain counts:
  `safety=26, operations=17, vehicle_body_planar_kinematic_comfort_proxy=7, controlled_benchmark_realtime=6`
- Evidence-class counts:
  `reconstructable_with_frozen_transform=42, evidence_missing=13, scientifically_inapplicable=1, directly_reconstructable=0`
- Contract canonical SHA256:
  `b6fcabdf40b035b2bd210db521f2f5fae5e36bbad30a736e78b23710da4b2c7e`
- Capability matrix canonical SHA256:
  `d23ee57e1e9c8411af255ec686b8835124d028ff42c88f6525cdaecd6beaaa4b`
- New weighted total:
  `false`
- Legacy SafetyCost role:
  `immutable_legacy_exploratory_diagnostic_only`
- Numeric margin:
  `numeric_margin_not_authorized_until_future_preregistration`
- Complete-case claim:
  `false`
- Full-denominator missing retention:
  `true`

## Superseded local diagnostic inventory

This inventory is deliberately outside all accepted amendment roots. It was
not staged or committed, and local tracked-clean is therefore
`false_due_to_preserved_superseded_training_support_draft`.

- Tracked modified files: `2`
- Untracked diagnostic files: `9`
- Preserved diagnostic tests: `39/39`
- Model/pool/selector calls: `0`
- Included in accepted amendment roots: `false`
- Canonical inventory SHA256:
  `6eba8cfa4c232fc7c70ebc85755caf8117917081956302953f6d6173b81fbd13`
- Binary tracked diff SHA256:
  `f95ce26ec2658bdbece28f09a5f3b6766fecbfcd0178b21743ee24a4b6a8d3d1`

Per-file evidence is recorded in the report. The two tracked modified file
SHA256 values are
`085db0eb3984754f0655eca2daa4105f94fc36e6b0b192fee1cbb84c44cfac3f`
and
`3d67efa24ddbfbb6447542804d9460ef9826cc132b0c587d04b6f24ac392ca92`.
The nine untracked file SHA256 values are
`af69b98945fd42c3e9e18b9ed5249a4e89d4ded9b9271834d76f53f1cf0bed50`,
`0957ede15ec2d06919cff4ce51cf7d664713668029f1968b261cb2b4c3f32be4`,
`c2c7897c37b9cc8462661987b2bf4677fe1665e5eaaa6abc9746930b7b5cbf9d`,
`1947f8b91e2b122224de22e780050a64311ecd9c0783c1b59db18a1afeb3c61e`,
`e368d43018765ada3b71962ac4febfe1f4270db3da853d94f8bf1da9ff44e4b5`,
`1ea65c014b1df9c966a0ca74edf92d4442c4a6abd0f8cb97afd87afb5ec38a0d`,
`be7bb22998510ddedfb7380e3b5717471bde6958f0603417e8b44104f65bb5df`,
`dde14dc3be37de1895d29f3fc527917454fdd0492612590ed8f5c4e5ef93912b`,
and
`6d7678ae3ecd2d322bfa03f01d54b2a395c213079cfaaea9c8436b61de511fd1`.

## Documents

- Report:
  `docs/diffusion_planner_v25_industrial_evaluation_amendment_report.md`
- Migration matrix:
  `docs/diffusion_planner_v25_industrial_evaluation_migration_matrix.md`
- Future endpoint/prereg plan:
  `docs/diffusion_planner_v25_industrial_evaluation_future_prereg_plan.md`
- Current pointer:
  `docs/diffusion_planner_current_status.md`
- Audit:
  `docs/diffusion_planner_v25_iteration_audit.md`

Final document SHA256 values are recorded in the Current/Audit tuple after the
sealed implementation chain is complete.
