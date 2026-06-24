# DP Native Clean Training Log Collection Broader Nonformal Result

Date: 2026-06-24

Gate:

```text
dp_native_clean_training_log_collection_broader_nonformal_user_authorized_execution
```

This artifact records the user-authorized broader nonformal clean-log
collection. It ran replay only inside the explicit approved envelope and did
not run CAMP retraining, Diffusion Planner modification, selector/atom
promotion, Full36, formal seeds 11/12/13, reference_blend, guidance, or any
safety/CAMP-over-DP claim.

## Fixed Artifact Root

```text
/root/autodl-tmp/camp_dp_native_clean_training_log_broader_nonformal_4967c531_20260624T054110Z
```

## HEAD Evidence

```text
local/GitHub/AutoDL CAMP pre-run HEAD=4967c531d51d098fa836de134d9e7380a448f8ee
AutoDL CAMP origin/main=4967c531d51d098fa836de134d9e7380a448f8ee
AutoDL DP HEAD=7a1d33da277a1992ec474b5383a0c963c72e04e4
required DP fixed commit=7a1d33da277a1992ec474b5383a0c963c72e04e4
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
routes=sample_tl,sample_normal
sample_tl=/root/autodl-tmp/camp_dp_assets/sample_map_tl_route_59_to_86.pkl
sample_normal=/root/autodl-tmp/camp_dp_assets/sample_map_route_2_to_104.pkl
seeds=101,102,103
traffic_lights=on,off
steps=3
num_candidates=4
candidate_noise_strategy=iid
candidate_noise_scale=1.0
advance_mode=perfect
max_npcs=0
spawn_probability=0.3
camp_selector_mode=uniform
camp_atom_scales=/root/autodl-tmp/camp_dp_assets/camp_dp_robust_static_v10_progress2_redstopfloor05_j1_lat2_e70f263/atom_scales_dp_static.json
camp_feasibility_source=dp_reward
reward_config=/root/autodl-tmp/camp_core/configs/integrations/dp_camp_reward_eval.json
must_enable=--camp_candidate_tensor_provenance_logging
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
safety or CAMP-over-DP claim
```

## Result

```text
collection_passed=True
run_count=12
all_replay_exits_zero=True
selection_log_count=12
all_selection_logs_present=True
total_records=36
expected_exact_selection_records_for_completed_matrix=36
validator_exit=0
validator_passed=True
validator_records=36
validator_failed_records=[]
future_training_input_contract_satisfied=True
```

Coverage counts:

```text
counts_by_route={"sample_normal": 18, "sample_tl": 18}
counts_by_seed={"101": 12, "102": 12, "103": 12}
counts_by_traffic_lights={"off": 18, "on": 18}
candidate_count_values={"4": 36}
selected_index_counts={"0": 7, "1": 8, "2": 7, "3": 14}
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

The `validator_replay_executed=False` and
`validator_candidate_generation_executed=False` fields refer to the validator
itself. Replay and DP-native candidate generation were executed only in the
approved broader nonformal collection envelope above.

## Verification

Remote fixed-artifact verification:

```text
collection_driver_exit=0
clean_log_validator_exit=0
clean_log_validator_passed=True
clean_log_validator_records=36
```

Local narrow checks:

```text
git diff --check -- docs/diffusion_planner_v8_iteration_audit.md docs/dp_native_clean_training_log_collection_broader_nonformal_result.md
exit=0

python --version
Python 3.13.9

python -m py_compile scripts/integrations/validate_dp_native_training_data_contract.py camp_core/tests/test_dp_native_training_data_contract_validator.py
exit=0

python -m pytest --rootdir=<temp> <temp>/tests/test_dp_native_training_data_contract_validator.py -q
8 passed in 0.76s
exit=0
```

The direct Windows repo pytest invocation for the same target aborted before
collecting the target file because pytest enumerated a pre-existing unavailable
long-path test node unrelated to this documentation-only change. The target
test was therefore run with a temporary rootdir copy and the repo on
`PYTHONPATH`; no repo files were cleaned or modified for that workaround.

AutoDL narrow checks:

```text
PYTHONDONTWRITEBYTECODE=1 /root/autodl-tmp/dp312_venv/bin/python -m py_compile scripts/integrations/validate_dp_native_training_data_contract.py camp_core/tests/test_dp_native_training_data_contract_validator.py
REMOTE_PY_COMPILE_EXIT=0

PYTHONDONTWRITEBYTECODE=1 /root/autodl-tmp/dp312_venv/bin/python -m pytest camp_core/tests/test_dp_native_training_data_contract_validator.py -q
8 passed in 0.41s
REMOTE_PYTEST_EXIT=0
```

## SHA-256 Evidence

Fixed root files:

| Artifact | SHA-256 |
| --- | --- |
| `preflight.json` | `163162dfc60bd7967773fe12834a58b7c6debe785bd58af55eeb99ff879fe965` |
| `collection_summary.json` | `05c8c7056dbe7460cfac422b0f1081179021a9df80324a4378cec3bf6dc693f0` |
| `collection_summary.md` | `be8e8acc22805592c35ec22d71d86f494fd53768fad8cf0a8c338e3bfd89363a` |
| `clean_dp_native_training_data_contract_validation.json` | `c2f8f1b10e9d1a8925886255e8ffa3af151ef1ceaab278027a50a9087f39a7f4` |
| `clean_dp_native_training_data_contract_validation.md` | `76e14ed1657d91581b2ff96cfcf0366be2363d704e4a38d2ea7e5f7659263758` |
| `validator_stdout_stderr.log` | `5b7b916da344996d04f5950c723cfde782ca981c57fccbc8c8cacb174ed0a458` |
| `validator_exit.txt` | `9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa` |

Per-run replay exits, selection-log SHA, and replay-log SHA:

| Route | Seed | TL | Exit | `camp_selection_log.json` SHA-256 | `replay_stdout_stderr.log` SHA-256 |
| --- | ---: | --- | ---: | --- | --- |
| `sample_tl` | 101 | on | 0 | `a3b7cddfcfb3b877c1210f957dc8656b5bcb7747ecdfe1993b04fbef17b32ea6` | `9624fda933917caebb63d07b705362dba60db87e4d8fd5c9fd8ef5b16f25195d` |
| `sample_tl` | 101 | off | 0 | `722f7e70330fe08cc42d92c3ab3b4c00d4c24e825d493607e26ce07272bcb0a1` | `5e24126963a3634317a4ac75c9a9ffd89fd1c0a43eb4875ac4687fbee0021111` |
| `sample_tl` | 102 | on | 0 | `712b4d0bca44077bd8db9b365e96089ce6b4d0cc2fb61adcde3f7615e9f84ec9` | `98e578afd6cf9d24ca4313847bb6aabe00ccf096372bf2d50e7b459ea4beb7f2` |
| `sample_tl` | 102 | off | 0 | `466bb7a242fe7fb75d98a8b315eb1ffdb47947048f322e921ead27401107667c` | `2e16e08a9862e6979ed98571f3f51515a1abc5a0065b948e14e4633ad0d3c6a2` |
| `sample_tl` | 103 | on | 0 | `598eca1e7b68cd70d2bdc2ac4006cc85e8d3601357b61b4d5aeff6e71e5ffa44` | `1aa7a5276026e0dbbcf44b532e3b92f2bdb6167ee1341dfd28b4b2487219cb5e` |
| `sample_tl` | 103 | off | 0 | `d3a140040b16e2715ebbcb56d58b908233bb37796d4a6f385bdbb4ec45a7fe86` | `1b5c3a575199c2fed4d08b1b9531d887e9942071d4a31126c34eebde0e035592` |
| `sample_normal` | 101 | on | 0 | `06df752425bc048985c130d877bf6ec853fc54e4bddff43b0fa65f7ca14aba0f` | `4189f57f80bd68c6b49f0d0f7e99f6bcc29664314edef9ad263dfd2790d1ec5f` |
| `sample_normal` | 101 | off | 0 | `7d301ab9ec5b03874f3e82ed03869970f3cdedeca5bf3d82d03637f6967a02f5` | `3aa128974375a561778cfb70f9e6011f20f1c7ef0a35bbedf61f2905e634b8f3` |
| `sample_normal` | 102 | on | 0 | `a021db9bb46f0c10b84b5a3b253a6e8ea118595c1161330d726ebc49de40fbfa` | `bb63cf9480e0f60a180cb43f3bf6d2572c024864813e3bf89ca4eb0085fc7fdf` |
| `sample_normal` | 102 | off | 0 | `f74e5e953c64f8bc84ce884aa5e52686f9a19b878dcf61b9485925a6e5464f96` | `0250e8ac00e527f648f26441eb0709b370721a2d77559fdd919e594d03ab0332` |
| `sample_normal` | 103 | on | 0 | `7ad23dda677f039b64bbede492a67865b498570f110c4826dd5689430dd88b24` | `c705f92ec0bff0e686c64171f8c32003183adca8b0a1b012171643a042289a20` |
| `sample_normal` | 103 | off | 0 | `67dbccdf11a3dcc7da05e3e0c1db6fb185f1b6a4d5fdb6dc3eae066d47aa0e1e` | `052e127a365dece0f2be90c2b360654bd475a95e7c9c42d826a6067a62b298f0` |

## Decision

```text
status=broader_nonformal_collection_passed
clean_dp_native_training_log_contract_passed=True
records_collected=36
training_execution_authorized=False
camp_retraining_authorized=False
online_selector_promotion_authorized=False
atom_promotion_authorized=False
dp_modification_authorized=False
safety_benefit_claim_authorized=False
camp_over_dp_top1_claim_authorized=False
```

This result is sufficient evidence that the clean DP-native logging path can
produce a small broader nonformal training-log set under the approved boundary.
It is not, by itself, authorization to train CAMP or to make performance,
safety, or CAMP-over-DP claims.

## Next Gate

`dp_native_clean_training_log_dataset_sufficiency_and_trainer_preflight_authorization_only`

The next gate should be read-only unless separately authorized. It should audit
the fixed broader nonformal artifacts for dataset sufficiency, grouping/split
rules, duplicate or leakage risk, selector-label semantics, and trainer
preflight requirements before any CAMP retraining is considered.
