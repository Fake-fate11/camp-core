# V25 Fresh B4 Metric-Semantics Amendment Report

Date: 2026-07-25 (Asia/Shanghai)

Status: `sealed_read_only_metric_semantics_amendment`

Schema: `camp_dp_v25_metric_semantics_amendment_v1`

Final scientific decision (unchanged):
`honest_no_claim_under_frozen_preregistered_all_gate`.

## 1. Scope and non-retroactivity

This additive amendment changes the interpretation and reporting vocabulary of
the already sealed Fresh B4 measurements. It does not change any legacy value,
model, atom, scale, weight, threshold, NI margin, multiplicity rule, split,
denominator, claim rule, execution artifact, corrected-evaluation artifact, or
CAS ledger.

The exact sealed denominator is reused read-only: 500/500 paired units,
1,500/1,500 complete and terminal arms, and 96,000 ticks. Fresh execution,
DP/K8, corrected evaluation, and corrected-evaluation review were not rerun.
The legacy corrected report and evidence index remain byte-preserved.

Static14D and Scene14D retain their immutable project-defined SafetyCost
deltas:

| Arm vs candidate0 | Mean delta | Clustered 95% CI | B/T/W |
|---|---:|---:|---:|
| Static14D | -2.5299346354001058 | [-3.551884242964027, -1.5079850278361844] | 280/81/139 |
| Scene14D | -1.2135901546149832 | [-2.132750489352197, -0.29442981987776917] | 227/111/162 |

These numbers mean only that the legacy project-defined composite decreased
inside this fixed 64-tick controlled benchmark. They do not establish
industrial safety improvement. Both arms still fail the frozen all-gate:
`component_all=false`, `NI_all=false`, safety claim=false, and red-light
claim=false. This amendment introduces no new confirmatory gate or claim.

## 2. Industrial-semantics disposition matrix

`PASS` below means that the named source or inference construction is
technically supported for its stated narrow scope. It never means vehicle
type approval or certification.

| Item | Exact class | Accurate interpretation |
|---|---|---|
| SafetyCost | benchmark-only | `100*collision_any + 10*near_tick_rate + 20*offroad_tick_rate + 20*wrongway_tick_rate + 30*red_any + 10*speed_tick_rate`; project-defined mixture of run-level any-events and tick rates |
| Collision | benchmark-only | `simulation_obb_overlap_any`; OBB clearance `<=1e-6`, without physical severity, sensor/dynamics qualification, or type testing |
| Near miss | FAIL-industrial | Legacy alias becomes `noncollision_obb_clearance_le_2m_tick_rate`; no TTC, PET, speed, or relative-motion condition |
| Offroad | FAIL-industrial | Legacy alias becomes `five_point_drivable_coverage_failure_tick_rate`; center plus four corners is not a full footprint/polygon-union test |
| Wrong-way | FAIL-industrial | Legacy alias becomes `nearest_route_segment_heading_opposition_moving_onroad_tick_rate`; nearest-segment matching can be ambiguous at junctions or parallel segments |
| Red-light source authority | PASS | Same-tick certified signal phase plus exact route stop-line, with no future phase consumed |
| Red-light aggregate | benchmark-only | `certified_red_phase_stopline_crossing_gt_0_5mps_any`; the 0.5 m/s gate excludes slower crossings, and the interval denominator is not a legal violation rate |
| Speed | benchmark-only | `onroad_speed_excess_gt_0_1mps_tick_rate`; 0.1 m/s is a project operational tolerance, not an ISA/type-approval threshold |
| Progress/completion | benchmark-only | `final_nearest_route_polyline_projection_m` and `clipped_final_route_projection_fraction`; nearest-segment projection is not route-order state |
| Jerk | FAIL-industrial | Legacy scalar-speed second difference is only `raw_longitudinal_speed_second_difference_chatter_diagnostic` |
| Lateral acceleration | FAIL-industrial | Legacy `abs(speed*yaw_rate)` is only `raw_speed_times_heading_rate_lateral_kinematic_diagnostic` |
| Maximum deceleration | FAIL-industrial | Legacy one-tick speed drop is only `raw_same_tick_scalar_speed_drop_peak_deceleration_diagnostic` |
| Latency | benchmark-only | Controlled AutoDL `perf_counter_ns` stage timing; not a production deadline or certification result |
| Online/production readiness | FAIL-industrial | At a hypothetical 10 Hz deadline, Static14D/Scene14D total p95 of about 607/614 ms exceeds 100 ms |
| Clustered statistics | PASS | Frozen-benchmark inference only: 100 equal-mass independent corridor/intersection cluster means, Student-t CI, paired B/T/W |
| Full-polygon offroad | evidence-missing | Sealed evidence cannot reconstruct a footprint-polygon union, so no approximation is fabricated |
| Occupant/seat/vertical comfort | evidence-missing | Suspension, seat and human transfer, vertical motion, and rotational coupling are not modeled |

The controlled benchmark is narrower than scenario-based ADS evaluation and
ODD evidence frameworks, and it is not a UNECE type-approval test. See
[ISO 34502:2022](https://www.iso.org/cms/%20render/live/en/sites/isoorg/contents/data/standard/07/89/78951.html?browse=ics),
[ISO 34503:2023](https://www.iso.org/standard/78952.html), and
[UNECE Regulation No. 157](https://unece.org/transport/documents/2021/03/standards/un-regulation-no-157-automated-lane-keeping-systems-alks).
The speed-limit sensitivity is likewise not evidence of EU ISA conformity;
the latter has its own type-approval procedures and technical requirements in
[Commission Delegated Regulation (EU) 2021/1958](https://eur-lex.europa.eu/legal-content/en/ALL/?qid=1780885084924&uri=CELEX%3A02021R1958-20230921).

## 3. Immutable legacy namespace

Every legacy field and numeric value is copied exactly from corrected
evaluation, with its source root, original formula,
`deprecated_industrial_interpretation=true`, and an accurate alias.

| Legacy field | Accurate alias / formula |
|---|---|
| `safety.total` | `legacy_project_defined_controlled_benchmark_safetycost`; formula shown above |
| `safety.collision` | `simulation_obb_overlap_any`; `any(min_obb_clearance_m <= 1e-6)` |
| `safety.near_miss` | `noncollision_obb_clearance_le_2m_tick_rate`; `count(1e-6 < clearance <= 2m)/64` |
| `safety.offroad` | `five_point_drivable_coverage_failure_tick_rate`; `count(not five_point_drivable_coverage)/64` |
| `safety.wrong_way` | `nearest_route_segment_heading_opposition_moving_onroad_tick_rate`; coverage=true, speed>0.5 m/s, heading opposition |
| `safety.red_light` | `certified_red_phase_stopline_crossing_gt_0_5mps_any` |
| `safety.speed` | `onroad_speed_excess_gt_0_1mps_tick_rate` |
| `performance.progress` | `final_nearest_route_polyline_projection_m` |
| `performance.completion` | `clipped_final_route_projection_fraction` |
| legacy mean/max jerk | `raw_longitudinal_speed_second_difference_chatter_diagnostic_mean_abs/max_abs` |
| legacy mean/max lateral acceleration | `raw_speed_times_heading_rate_lateral_kinematic_diagnostic_mean_abs/max_abs` |
| legacy maximum deceleration | `raw_same_tick_scalar_speed_drop_peak_deceleration_diagnostic` |

The old combined label `performance/comfort NI` is retained only as an
immutable legacy claim-rule label. Semantically, route progress/completion
remain project-benchmark performance NI inputs. The jerk, lateral, and
one-tick deceleration values are raw diagnostics, not industrial comfort
measures. Their old pass/fail values are not an industrial comfort decision.

## 4. Vehicle-body kinematic proxy

The new `vehicle_body_kinematic_comfort_proxy` is post-hoc descriptive and is
not part of the frozen claim. Its signal is
`filtered_vehicle_body_acceleration`.

For each 64-tick run, using only sealed `position_xy`,
`ego_heading_rad`, and `dt=0.1 s`:

1. Form 63 interval velocities
   `u_(i+1/2)=(p_(i+1)-p_i)/0.1`.
2. Form 62 accelerations
   `a_i=(u_(i+1/2)-u_(i-1/2))/0.1`, for `i=1..62`.
3. Rotate each planar acceleration by `heading_i`:
   `long=ax*cos(h)+ay*sin(h)` and
   `lateral=-ax*sin(h)+ay*cos(h)`.
4. Apply a transparent, zero-phase, centered 11-point equal-weight
   1.0-second boxcar, valid-only. There is no padding or extrapolation.
   Therefore every run has exactly 52 filtered samples; boundaries are
   discarded.
5. Summarize each run first. Only then form paired values and the 100
   independent-cluster summaries. Ticks are never pooled as independent
   observations.

### 4.1 Per-arm descriptive means

Each cell is the mean of 500 per-run summaries.

| Arm / axis | signed mean | RMS | min | max | peak abs | abs p50 | abs p90 | abs p95 | abs p99 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| candidate0 longitudinal | 0.672948 | 1.133839 | -0.958044 | 2.169109 | 2.181653 | 0.844059 | 1.859118 | 2.007865 | 2.146827 |
| Static14D longitudinal | 0.603958 | 1.086790 | -0.969690 | 2.083257 | 2.121211 | 0.777755 | 1.803838 | 1.957550 | 2.085194 |
| Scene14D longitudinal | 0.652108 | 1.084997 | -0.909192 | 2.091658 | 2.102673 | 0.796739 | 1.785827 | 1.935736 | 2.065716 |
| candidate0 lateral | -0.014262 | 0.362311 | -0.559689 | 0.487704 | 0.764401 | 0.190791 | 0.661274 | 0.718218 | 0.755637 |
| Static14D lateral | -0.009296 | 0.330556 | -0.520502 | 0.473515 | 0.709707 | 0.182206 | 0.592251 | 0.654364 | 0.698372 |
| Scene14D lateral | -0.009910 | 0.341628 | -0.538967 | 0.481018 | 0.730855 | 0.186205 | 0.614535 | 0.674357 | 0.718652 |

### 4.2 Project sensitivity durations

Durations are `sample_count*0.1 s`, averaged over runs. Thresholds are a
descriptive project grid, not industrial limits, ISO/SAE exceedances, or
comfort gates.

| Arm | longitudinal abs >0.5/1/2/3 | lateral abs >0.5/1/2/3 | signed deceleration <-0.5/-1/-2/-3 |
|---|---|---|---|
| candidate0 | 3.5302 / 2.2054 / 0.4376 / 0.0000 | 0.8492 / 0.2132 / 0.0002 / 0.0000 | 0.5974 / 0.2032 / 0.0038 / 0.0000 |
| Static14D | 3.4206 / 2.0062 / 0.3706 / 0.0012 | 0.7378 / 0.1584 / 0.0014 / 0.0000 | 0.6472 / 0.2126 / 0.0162 / 0.0012 |
| Scene14D | 3.4684 / 2.0606 / 0.3496 / 0.0000 | 0.7800 / 0.1764 / 0.0010 / 0.0000 | 0.5670 / 0.1706 / 0.0032 / 0.0000 |

### 4.3 Selected paired cluster descriptions

These are descriptive paired summaries, not new NI or claim gates.

| Arm vs candidate0 | Measure | Mean delta | 95% CI | B/T/W |
|---|---|---:|---:|---:|
| Static14D | longitudinal RMS | -0.047049 | [-0.058473, -0.035625] | 383/0/117 |
| Static14D | longitudinal abs p95 | -0.050314 | [-0.083261, -0.017368] | 309/0/191 |
| Static14D | lateral RMS | -0.031754 | [-0.042226, -0.021282] | 329/0/171 |
| Static14D | lateral abs p95 | -0.063854 | [-0.086298, -0.041410] | 335/0/165 |
| Scene14D | longitudinal RMS | -0.048842 | [-0.057519, -0.040166] | 396/0/104 |
| Scene14D | longitudinal abs p95 | -0.072129 | [-0.095114, -0.049143] | 359/0/141 |
| Scene14D | lateral RMS | -0.020683 | [-0.028609, -0.012757] | 319/0/181 |
| Scene14D | lateral abs p95 | -0.043861 | [-0.061546, -0.026177] | 309/0/191 |

This planar kinematic proxy is not seat, occupant, or whole-body response.
Suspension response, seat/back/feet transfer, vertical acceleration,
roll/pitch/yaw rotational coupling, and human frequency weighting are
`not_modeled`. ISO 2631 and SAE J2834 conformity are `not_assessed`; industrial
occupant comfort is `evidence_missing_not_assessed`. ISO 2631 addresses
whole-body vibration, while SAE J2834 covers periodic, random, and transient
whole-body vibration, its measurement/transducer conditions, and transmission
through body contact points. See [ISO 2631-1:1997](https://www.iso.org/standard/7612.html)
and [SAE J2834](https://saemobilus.sae.org/standards/j2834_201310-ride-index-structure-development-methodology).
The scalar-speed jerk and one-tick deceleration diagnostics also do not
establish ACC conformance under
[ISO 15622:2018](https://www.iso.org/standard/71515.html?browse=tc).

## 5. Read-only safety and route extensions

### 5.1 Clearance

The table reports mean duration in seconds and mean contiguous-episode count
per run at descriptive clearance thresholds. A 2 m event is not automatically
called a near miss.

| Arm | duration <=0/0.5/1/2 m | episodes <=0/0.5/1/2 m |
|---|---|---|
| candidate0 | 0.0002 / 0.3940 / 0.5980 / 0.7850 | 0.002 / 0.536 / 0.456 / 0.478 |
| Static14D | 0.0000 / 0.3312 / 0.5074 / 0.7272 | 0.000 / 0.488 / 0.418 / 0.462 |
| Scene14D | 0.0000 / 0.3816 / 0.5558 / 0.7708 | 0.000 / 0.510 / 0.450 / 0.476 |

Per-run minima are preserved in the sealed artifact. Their arm mean is not
used here because no-obstacle ticks carry a finite sentinel, making such an
arm-mean minimum misleading. Full-polygon offroad remains
`evidence_missing`; the five-point proxy is not promoted into one.

### 5.2 Certified signal binding and red crossings

| Arm | red-phase intervals | unthresholded crossings | crossings >0.5 m/s | mean per-run crossing/red-interval rate |
|---|---:|---:|---:|---:|
| candidate0 | 18,048 | 228 | 228 | 0.00712500 |
| Static14D | 18,048 | 193 | 193 | 0.00603125 |
| Scene14D | 18,048 | 213 | 213 | 0.00665625 |

Counts and denominators are separate. The artifact also preserves conditional
crossing-speed summaries and minimum stop-line margin. The same-tick
certified-phase/exact-stop-line binding is strong benchmark source evidence,
but neither the interval rate nor the >0.5 m/s any-event is called a legal or
type-approval violation rate.

### 5.3 Speed protocol

The sealed native `speed_protocol_v22` is reported at strict and
0/0.05/0.1/0.2 m/s sensitivity plus continuous magnitude-duration measures.
Values below are per-run arm means.

| Arm | event rate at 0/0.05/0.1/0.2 m/s | max excess m/s | mean excess m/s | excess duration s | magnitude-duration m |
|---|---|---:|---:|---:|---:|
| candidate0 | 0.064400 / 0.063430 / 0.062673 / 0.060648 | 0.166054 | 0.047979 | 0.3136 | 0.237039 |
| Static14D | 0.053116 / 0.051877 / 0.049804 / 0.046765 | 0.125024 | 0.029991 | 0.2602 | 0.148051 |
| Scene14D | 0.062185 / 0.061071 / 0.059876 / 0.057153 | 0.160236 | 0.040822 | 0.3038 | 0.202920 |

The same-tick map speed-limit source supports this controlled benchmark only;
it is not EU ISA/type-approval evidence.

### 5.4 Route projection and traveled distance

Values are per-run arm means.

| Arm | final projection m | clipped fraction | net projection m | max-first m | backtracking duration s | backtracking distance m | distance traveled m |
|---|---:|---:|---:|---:|---:|---:|---:|
| candidate0 | 37.511727 | 0.294961 | 37.011727 | 37.011727 | 0 | 0 | 37.077845 |
| Static14D | 36.491347 | 0.286911 | 35.991347 | 35.991347 | 0 | 0 | 36.052912 |
| Scene14D | 37.152647 | 0.292110 | 36.652647 | 36.652647 | 0 | 0 | 36.715619 |

The paired legacy delta remains valid because paired arms share the same
starting condition. Static14D net projection delta is -1.020380 m, clustered
95% CI [-1.391984, -0.648776], B/T/W 356/0/144; Scene14D is -0.359080 m,
[-0.579440, -0.138720], 302/0/198. These are controlled-benchmark performance
descriptions, not broad ODD generalization.

## 6. Latency and inference scope

The sealed controlled AutoDL timing remains:

| Arm | total mean / median / p95 / p99 / max ms |
|---|---|
| candidate0 | 68.800894 / 68.348749 / 72.232599 / 75.897811 / 518.258393 |
| Static14D | 531.782756 / 518.678487 / 607.223826 / 755.545621 / 993.904560 |
| Scene14D | 536.456213 / 522.531789 / 613.830395 / 755.155321 / 1072.831110 |

These are benchmark measurements, not production deadlines. If 10 Hz is
treated as a 100 ms real-time cycle, Static14D and Scene14D p95 are well above
that budget, so online/production readiness is `FAIL-industrial`.

Clustered inference is valid only for the frozen benchmark: 100 equal-mass
independent corridor/intersection cluster means, Student-t confidence
intervals, and paired B/T/W. It does not treat ticks, seeds, or arms as
independent and does not justify real-road, broad unseen-map, or regulatory
generalization.

## 7. Provenance and independent review

- Implementation HEAD: `b729ebe4ca34615453a8f7252585bdb5f30d3ac9`
- Fixed DP HEAD: `7a1d33da277a1992ec474b5383a0c963c72e04e4`
- Execution root: `e1bc886bd4d6d44b9bff703db7bbbfdb5117224bda1c5af5fb6524b0ed759881`
- Execution-review root: `f0afc12a15eba589b5fc63750477b60d0ba9b69cbd22b2e17bd87fadc761d98d`
- Corrected-evaluation root: `4a817b4bbd17449486e3258c0d4b07102929d5f12d60fa4bb73056eb726afb9f`
- Corrected-evaluation-review root: `94b048ace4a2a539532ccc64fe061afb51bc6b4e23ee2e5a5affd1fc2ef69459`
- Outcome-independent contract root: `318e85f9656a5dd79c9fb0ad6c1dfcd94678b35c4aba455f3909cf3475cca758`
- Contract independent-review root: `fc04fd6e45487df6c9bf5313b9ee6d633f91303e0a1aa00f0a3114b8134fea95`
- Read-only amendment root: `99fd5e571160a3ac3d5bb2b6d6f3391c3da5965bf592707ff85c88080ac2dbcf`
- Amendment independent-review root: `88b35ab8ef51807c848200675ceeebe6b26e15a4f4b34da51f131e9303f37898`
- Implementation-focused AutoDL tests: 31 passed; root
  `896fa3858a427462ecd4d3b206208605864fb34f3a4a5dd43ca723ec30445e95`
- Continuation ledger SHA (unchanged):
  `727ac337bfbd2bace321d45127c84b5b36d28522750f5e8ba445d1259248c392`

The separate-role amendment reviewer independently reconstructed the field
set, formulas, root bindings, 64->63->62->52 sample accounting, body-frame
rotation, legacy equality, per-run summaries, paired cluster summaries, and
claim invariance. It did not merely trust the producer summary.

## 8. Final boundary

The final result remains
`honest_no_claim_under_frozen_preregistered_all_gate`.
The amendment is not a retrospective authorization of a Fresh benefit claim,
and it is not an industrial comfort verdict. No claim is made for real-road
safety, broad unseen-map/ODD performance, native-ranked Top1, ISO/SAE
conformity, promotion, deployment, online activation, or production readiness.
