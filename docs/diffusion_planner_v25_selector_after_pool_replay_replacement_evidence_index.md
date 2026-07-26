# V25 Selector-After-Pool Replacement Evidence Index

| Role | Exact directory | Root SHA256 | Result |
|---|---|---|---|
| preserved failed replay | `/root/autodl-tmp/camp_dp_v25_selector_after_pool_replay_v1_59874f4a` | `7a85ef00c10a79aa1b8e92729f51d9512e5e67d53d1ef44e00da55d19840109d` | preserved typed failure |
| failure closeout | `/root/autodl-tmp/camp_dp_v25_selector_after_pool_replay_failure_closeout_v1_4c412870_e6579ca7` | `c9e70e5d96d88c6701084f975e48004728be9a0a452f6cead580f3bbf7c11016` | PASS |
| independent failure review | `/root/autodl-tmp/camp_dp_v25_selector_after_pool_replay_failure_closeout_review_v1_4c412870_e6579ca7` | `d914cc42bcbca494cffa4ba7a089b609dc28c6bf389e4b107f67b99d08587e00` | PASS |
| replacement contract | `/root/autodl-tmp/camp_dp_v25_selector_after_pool_replay_replacement_contract_v1_4c412870_e6579ca7` | `05e3c4b15d164118e54e724cb8868e36ad593f5a4e13823cb1b9b7be23b2bfa4` | PASS |
| independent contract review | `/root/autodl-tmp/camp_dp_v25_selector_after_pool_replay_replacement_contract_review_v1_4c412870_e6579ca7` | `de11309d646735dd8effe345d067ee7745068df923273da663c0fb947e987647` | PASS |
| implementation focused | `/root/autodl-tmp/camp_dp_v25_selector_after_pool_replay_replacement_focused_v1_4c412870_e6579ca7` | `c0b107cc5302335ace66d5d0af930fdb04f4d7177544a80fa7f316aae9615f7e` | 31/31 PASS |
| replacement preflight | `/root/autodl-tmp/camp_dp_v25_selector_after_pool_replay_replacement_preflight_v1_4c412870_e6579ca7` | `062d2afd94966f89259495ef3b092ba5c324ee748a64d77914e01f859f5f19eb` | PASS |
| independent preflight review | `/root/autodl-tmp/camp_dp_v25_selector_after_pool_replay_replacement_preflight_review_v1_4c412870_e6579ca7` | `60f5fd098086dcbfe47b7c3200d8ef5116c389e14164fdd123dc90a553f45e08` | PASS |
| replacement replay | `/root/autodl-tmp/camp_dp_v25_selector_after_pool_replay_replacement_v1_4c412870_e6579ca7` | `9e89135981ace29e86ec6b0b270d17aad4ac089d8fbdec10d98a0aa14c3a0982` | PASS |
| independent replay review | `/root/autodl-tmp/camp_dp_v25_selector_after_pool_replay_replacement_review_v1_4c412870_e6579ca7` | `3d2ac16d055f9957941d0d84b0b47282413a41559e47e67ce9a644ae8e3bc80b` | PASS |

## Immutable input authorities

- corrected raw/review:
  `731a715a0422f92e115bc078900d84c47b9f51f47c64181c3b8e71569cffdda4`
  / `c0e24bb60a4eb9694bfda099d4d6d9b9be07f85fb486577275f0b32178cfbfc8`;
- accepted training/review:
  `8d2d9ee3ed83fbe4270cb96b7bc6ef6619e5180f11ebc348b9bdea136bac4da9`
  / `ef2e9748a9ba0fff5b35f010cba6efd1b16d8e1dc0d562f5a7960c8dcb3d9be9`;
- 14D scales file:
  `72694a5f21c0f99d6506ed078b53e75c76f26319005e9a0dd7cbc30ca7f688eb`;
- fixed DP:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.

## Denominator and call accounting

| Item | Value |
|---|---:|
| states | 64 |
| repeats per state | 5 |
| completed slots | 320/320 |
| candidate0 structural selections | 320 |
| Static selector calls | 320 |
| Scene selector calls | 320 |
| total selector receipts | 640 |
| typed failures | 0 |
| nondeterministic states | 0 |
| tensor mutations | 0 |
| model/DP/latent/candidate-generation calls | 0 |
| outcome reads | 0 |
| upstream artifact/CAS writes | 0 |

The old replay's 320 typed failures remain evidence of a preselector tolerance
wiring defect only. The replacement PASS is limited to the sealed-pool runtime
compatibility, immutability, zero-extra-call and determinism boundary described
in the report.

The future industrial-v3 closed-loop hardening requirement is recorded but is
not authorized, executed, sealed or treated as a gate by this package.
