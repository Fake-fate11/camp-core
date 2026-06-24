# DP Native Training Sufficiency Development Collection Result

Date: 2026-06-24

Gate:

```text
dp_native_training_sufficiency_development_collection_user_authorized_execution
```

This artifact records the user-authorized DP-native development collection. It
ran only the approved clean replay envelope from
`docs/dp_native_training_sufficiency_development_clean_collection_scope_plan.md`
and then ran the clean contract and development profile validators. It did not
run CAMP retraining, closed-loop outcome collection, reference_blend, guidance,
postprocess/postselection, Full36, formal seeds 11/12/13, Diffusion Planner
modification, selector/atom promotion, or any safety/CAMP-over-DP claim.

## Fixed Artifact Root

```text
/root/autodl-tmp/camp_dp_native_training_sufficiency_development_collection_73aec55_20260624T075109Z
```

## HEAD Evidence

```text
local_HEAD=73aec557ff32e69c4735a38eee29f372da6a4f6c
origin_main=73aec557ff32e69c4735a38eee29f372da6a4f6c
github_refs_heads_main=73aec557ff32e69c4735a38eee29f372da6a4f6c
autodl_CAMP_HEAD=73aec557ff32e69c4735a38eee29f372da6a4f6c
autodl_CAMP_origin_main=73aec557ff32e69c4735a38eee29f372da6a4f6c
autodl_DP_HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4
required_DP_fixed_commit=7a1d33da277a1992ec474b5383a0c963c72e04e4
```

Remote preflight status:

```text
CAMP status:
## main...origin/main
untracked unrelated prior-session artifacts remain ignored

DP status:
## tier4-main...origin/tier4-main
```

## Authorized Scope Actually Run

```text
routes=sample_normal,sample_tl,nishishinjuku_lane_change
sample_normal=/root/autodl-tmp/camp_dp_assets/sample_map_route_2_to_104.pkl
sample_tl=/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl
nishishinjuku_lane_change=/root/autodl-tmp/camp_dp_assets/nishishinjuku_lane_change_route_7_via_8_to_1.pkl
seeds=101,102,103,104
traffic_lights=on,off
steps=5
num_candidates=4
candidate_noise_strategy=iid
candidate_noise_scale=1.0
advance_mode=perfect
max_npcs=0
spawn_probability=0.3
camp_selector_mode=uniform
camp_feasibility_source=dp_reward
must_enable=--camp_candidate_tensor_provenance_logging
expected_run_count=24
expected_max_selection_records=120
```

Forbidden flags/options were not present in the executed commands:

```text
--camp_collect_closed_loop_outcomes
--candidate_reference_blend_steps
--candidate_guidance_config
--candidate_guidance_scale
--camp_perfect_tracker_command_postselection
--camp_traffic_light_hybrid_postselection
--camp_underprogress_relaxation
--camp_splice_shadow_rule
Full36
formal seeds 11/12/13
CAMP retraining
Diffusion Planner code/config/weight change
selector/atom promotion
safety benefit claim
CAMP over DP Top-1 claim
```

## Result

```text
replay_collection_completed=True
run_count=24
expected_run_count=24
all_replay_exits_zero=True
selection_log_count=24
all_selection_logs_present=True
total_records=120
expected_max_selection_records=120
clean_contract_validator_exit=0
clean_contract_validator_passed=True
clean_contract_validator_records=120
development_profile_exit=1
development_profile_exit_expected=True
development_profile_passed=False
development_profile_records=120
development_profile_usable_feasible_records=72
development_profile_required_usable_feasible_records=100
development_profile_usable_feasible_record_gap=28
development_profile_failed_checks=["usable_feasible_records_at_least_min"]
```

Coverage counts:

```text
counts_by_route={"nishishinjuku_lane_change": 40, "sample_normal": 40, "sample_tl": 40}
counts_by_seed={"101": 30, "102": 30, "103": 30, "104": 30}
counts_by_traffic_lights={"off": 60, "on": 60}
candidate_count_values={"4": 120}
selected_index_counts={"0": 27, "1": 23, "2": 27, "3": 43}
```

Clean-boundary checks:

```text
no_forbidden_flags_in_commands=True
all_records_closed_loop_outcomes_none=True
all_candidate_generation_contracts_clean=True
all_candidate_tensor_provenance_clean=True
validator_read_only=True
validator_training_execution_authorized=False
validator_replay_executed=False
validator_candidate_generation_executed=False
```

The validator `replay_executed=False` and `candidate_generation_executed=False`
fields refer to the validators themselves. Replay and DP-native candidate
generation were executed only inside the user-approved collection envelope
above.

## Verification

Remote fixed-artifact verification:

```text
remote_replay_run_count=24
remote_all_replay_exits_zero=True
remote_selection_log_count=24
remote_clean_contract_validator_exit=0
remote_clean_contract_validator_passed=True
remote_development_profile_exit=1
remote_development_profile_exit_expected=True
remote_development_profile_passed=False
remote_development_profile_failed_checks=["usable_feasible_records_at_least_min"]
```

Local narrow checks:

```text
git diff --check -- docs/diffusion_planner_v8_iteration_audit.md docs/dp_native_training_sufficiency_development_collection_result.md camp_core/tests/test_dp_native_training_sufficiency_development_collection_result.py
exit=0

python -m py_compile camp_core/tests/test_dp_native_training_sufficiency_development_collection_result.py
exit=0

python -m pytest --rootdir=<temp-copy> <temp-copy>/camp_core/tests/test_dp_native_training_sufficiency_development_collection_result.py -q
3 passed in 0.03s
exit=0
```

The direct Windows repo pytest invocation for the same target aborted before
collecting this test because pytest enumerated a pre-existing unavailable
long-path test node unrelated to this documentation-only change. The target
test was therefore run from a temporary copy containing only the target test
and target doc; no repo files were cleaned or modified for that workaround.

## Remote SHA-256 Evidence

Fixed root files:

| Artifact | SHA-256 |
| --- | --- |
| `preflight.json` | `6e6da5f86b3c317842a01018b71141e4a04752e193d8459139df0d470b41a314` |
| `collection_summary.json` | `363dcc3a81cc737e6962c983d77425f59e56f4acccd56200bb15397edbe05dc8` |
| `collection_summary.md` | `7b02c84b128137c4d4dabfe2fe0e1f1355c8d333f33928bf970a5c17af7f9fbd` |
| `clean_dp_native_training_data_contract_validation.json` | `056262e969d4084e5ecd971c2c9bddafd0d9b63c0049744069aacffde5773014` |
| `clean_dp_native_training_data_contract_validation.md` | `8406955ffc91b7ae59cf28697c1f936b9a80a88aa2466b445626fef3af5c3378` |
| `clean_validator_exit.txt` | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |
| `clean_validator_stdout_stderr.log` | `019e2bda9b896e978314b142dc1ba13a62a10b17988c6a190366e3c7d2eb6573` |
| `development_profile_validation.json` | `2f62ab3575f5264faed34d6110fbba9ff8d552ea1b76585b0b488f5c61ce0259` |
| `development_profile_validation.md` | `e36246bb286976539aca295495ae6d9de1d8e28f0f6dc8be67965078876eacf8` |
| `development_profile_exit.txt` | `4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865` |
| `development_profile_stdout_stderr.log` | `d6b6e9d726f6efaaf1fef91c0f1955c84613b9a0544a876ce2af1534d33f9f39` |

Per-run replay exits, selection-log SHA, and replay-log SHA:

| Route | Seed | TL | Exit | `camp_selection_log.json` SHA-256 | `replay_stdout_stderr.log` SHA-256 |
| --- | ---: | --- | ---: | --- | --- |
| `nishishinjuku_lane_change` | 101 | off | 0 | `b5e9e19cad7ea38bbac9425baed3e1d6dcd0d0137fd7554ad663cece041adf41` | `a5caa9420b34b6b08fa885870c7a385e16818012260031423c7658ca44e1fe5f` |
| `nishishinjuku_lane_change` | 101 | on | 0 | `51b5eebe4e2447cf9e46167228e2ed00cfffe00e7859047e7bf5079d46bfce49` | `7821bb28d4c2a52407cdd712581993edbfabc4c67bfb8e6467388344f7cd055e` |
| `nishishinjuku_lane_change` | 102 | off | 0 | `492c1bd100d3bb6f3553830197a9838d6a5db5592b3dd61dc31ad6e0919bb0ea` | `8337e526fde2fc00d77dc074fb96ad70e20905d5e18e1141a01c17121cb99a94` |
| `nishishinjuku_lane_change` | 102 | on | 0 | `f0d852ea41d5dab233aceef3c7724099c920cac765381782efd7c46c8f01bfac` | `6c1ca9f43ee3e19468f7a78cd5876b83ada7b9ea02de4a73c6c1ae9b5e6419ad` |
| `nishishinjuku_lane_change` | 103 | off | 0 | `daccb0c650d4a6c0fb72f26acd13a9b5ee1a96037bd77d1a12c649d14344aedf` | `82c5bdee7dc4ba61ac620327afd79377011730e9ec7308177d480e19456f7632` |
| `nishishinjuku_lane_change` | 103 | on | 0 | `e02ef7058ff9bbbccb13e3b1938d206473e59a82adb5518d774345c13cb70822` | `31997122f7f3473e88ca0f3f1972f72275e476864c254f3c78cfa21652fbbdd9` |
| `nishishinjuku_lane_change` | 104 | off | 0 | `f7aa8495af97d43d74c45f62f7a23398795fdc640d9fc53b2a257b26fa080a48` | `edf8284e2abbf4fc891008375dca971bced6ad1a2038d1a387db51da7ceaac52` |
| `nishishinjuku_lane_change` | 104 | on | 0 | `5cd707ef16a2746ce7fcd6dae0c040ca6300bf15f934335ea6a74b27e6c3dc2e` | `669d7a533b8a5fa449860c88f736ce0fe8ea0add56a3248f10c53156df0fb2ee` |
| `sample_normal` | 101 | off | 0 | `dda5bd158b9e9bd291dfa1b7edeeef116d905aa56e1240775280762f545aa442` | `b4fb30471e034ada8521e15c22d012cb04928195131635788e66efb854601476` |
| `sample_normal` | 101 | on | 0 | `fafa88c27c020c0e6f80112eec68a35d2c9566b36a7dc22b9a25a0c1d6513a3d` | `ef44fcef4d22b736f74c775b3e32c0289dcd18ed8151cd408b041689a0099a81` |
| `sample_normal` | 102 | off | 0 | `b716c62781a7eb609318a261ccf95fea24ed6b34758d785bb13a5e6389a09171` | `15c59c0e2dab21f796895b68dc0ef459cfa3e50853c494e69eefa712488115cd` |
| `sample_normal` | 102 | on | 0 | `9affb739f2c03a08bc8e136a138712edde971fc8d6ece3a8aa8186011fb31e5a` | `9ab3cbccb852ab2b919a3eb9e0c9afd84d00cab7a236218c234ed70b7d127088` |
| `sample_normal` | 103 | off | 0 | `032e9aed5a9acd12b0b77ead2de4edfaa25b7c86059fab8312c0e0c05e458207` | `52fc92f71245cf998eb559bacf79a5be66c90fab25891453bcc214eeb1dc1677` |
| `sample_normal` | 103 | on | 0 | `7d9286c32a610994a0d18c8eb9b6464489604a9236ce32d0f854d1e014d30caf` | `305d4686ce69977923e58460f3e8d3d4bce94b0d960c003a794c720e6f325fc9` |
| `sample_normal` | 104 | off | 0 | `146221ba2e94df9cb84b9ba26eab76a434123dd45391cc82d12248d0bab99845` | `b108d065cef63624c8a662bd45c1a2ca3e390e05c330dbfded5bfceb99fb0d27` |
| `sample_normal` | 104 | on | 0 | `f4b2e151d14c32a3193321d180e4c9915fbfb58822b62f33a1aa5b6933ff1eb1` | `99f175d60e42573ce148cb751f9db7b8038bcc3e0580740042007e999237d252` |
| `sample_tl` | 101 | off | 0 | `bd15f5653a295fe5a642b811b7c48ffcb0e6d172c5f0dd8baaf81bdf258b0293` | `20dfe25ea1f0f5c9e62b4a5ec0b7fba10fde74bc7ab87fb6d71ae2645f25940b` |
| `sample_tl` | 101 | on | 0 | `790566dd35c73522f165a093bc4010a13d75bebff8fe07940127cb51c569a72b` | `39066aa4b8063dd4b1d0e0cccd5740ccbc3483e67bc5eca7aa209da0d8968418` |
| `sample_tl` | 102 | off | 0 | `c468a2c79b8fbea1cc718bc5fa31a9c4148c7cc3421c7269216a987a3101d041` | `6703a16a9c2dd91b32f83165c91f09d1e94ed48d38a50fd2914e6774e6e99059` |
| `sample_tl` | 102 | on | 0 | `93ce6a5aedbbb343b469271563de4b65d727d7b1bb82a5f33d84df1f429b8ccb` | `71ad5ea24ee28777117a8cc83a7cfa80214a3266df5c6fc349f50e5ec29bab6e` |
| `sample_tl` | 103 | off | 0 | `3cc7afa3395a0b333aedfe29692aa2247aad5853973d0fab7a38a589de2ec688` | `9ca56ad03a8392dd14dff63178be769d0919a9aa645f5024f7339eb1845f0aaa` |
| `sample_tl` | 103 | on | 0 | `656ef62b5ea36ff4c31753a7f4473dfc4c176e1a9791636a248f98032b203c82` | `bf4695d2167eddab0b4f37c767d5474ad9ae920dc56298234f8be36abf7adb25` |
| `sample_tl` | 104 | off | 0 | `0f0a1db50af856dbbe684b60ce93f719142e12d075a15a5f82a6a6818483ce63` | `4b060d6126254f56ad8a3bb24c9342ce32eb67b6dd47cd868cc036d1930d5d09` |
| `sample_tl` | 104 | on | 0 | `5de71e803755369bf9d245eaa73a65e3f2062df5deefc818712f0fe87a6dd5d9` | `44d154eaf4009dac4deac7a47625d63e93ed3107d87586756425f452856148e6` |

## Decision

```text
status=development_collection_clean_contract_passed_profile_failed_fail_closed
clean_dp_native_training_data_contract_passed=True
development_profile=dp_native_feasible_ranking_development_minimal_v1
development_profile_passed=False
failure_class=usable_feasible_record_shortfall
hard_blocking_reasons=["usable_feasible_records_at_least_min"]
raw_record_count_sufficient=True
route_count_sufficient=True
seed_count_sufficient=True
traffic_light_state_count_sufficient=True
candidate_count_sufficient=True
usable_feasible_records_sufficient=False
training_execution_authorized=False
camp_retraining_authorized=False
collection_replay_authorized=False
candidate_generation_authorized=False
dp_modification_authorized=False
online_selector_promotion_authorized=False
atom_promotion_authorized=False
deployable_checkpoint_claim_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

The artifact is clean and profile-covered in raw count, route count, seed
count, traffic-light state count, and candidate count, but it is not sufficient
for CAMP retraining because only 72 records satisfy the usable feasible
criteria required by the development profile. This is a fail-closed data
sufficiency result, not evidence for any safety or CAMP-over-DP claim.

## Next Gate

`dp_native_training_sufficiency_development_collection_usable_feasible_shortfall_attribution_only`

The next gate should be read-only and use only the fixed artifact above. It may
attribute why 48 of 120 records are not counted as usable feasible under the
development profile, but it must not run replay, generate candidates, train
CAMP, change DP, promote selector/atoms, or make safety/CAMP-over-DP claims.
