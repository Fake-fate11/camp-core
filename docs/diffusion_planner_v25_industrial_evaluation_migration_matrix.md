# V25 Legacy-to-Industrial Evaluation Migration Matrix

This matrix is additive. Historical values, roots, and claims are immutable.

| Historical item | Preserved name / role | New primary replacement | Migration rule |
|---|---|---|---|
| SafetyCost weighted sum | `legacy_project_defined_controlled_benchmark_safetycost` | No weighted total; 56-endpoint vector | Never primary, PASS, claim, training support, or adaptation evidence |
| Collision any | `simulation_obb_overlap_any` | Full-polygon any + episodes + duration | Any-event cannot stand in for impact severity |
| Collision severity | unavailable | relative-speed proxy only if authoritative; delta-v/contact severity missing | Typed missing; no proxy relabeling |
| Near miss at 2 m | `noncollision_obb_clearance_le_2m_tick_rate` | Clearance, closing speed, geometry TTC, DRAC, exposure duration/episodes | 2 m and other grids are project-descriptive, not industrial gates |
| THW | unavailable | Unique same-lane leader THW | Missing without unique leader/lane authority |
| PET | unavailable | Frozen conflict-zone passage-time PET | Missing without conflict zone and both passage times |
| Red >0.5 m/s | `certified_red_phase_stopline_crossing_gt_0_5mps_any` | Unthresholded swept crossing, speed, encounter and phase denominators | Slow crossing remains a crossing |
| Five-point offroad | `five_point_drivable_coverage_failure_tick_rate` | Full footprint vs drivable union outside fraction, signed clearance, penetration | Five-point is never a polygon substitute |
| Nearest-route wrong-way | `nearest_route_segment_heading_opposition_moving_onroad_tick_rate` | Onroad/moving plus unique lane/route direction duration/episodes | Ambiguous direction becomes missing |
| Speed >0.1 m/s | `onroad_speed_excess_gt_0_1mps_tick_rate` | Max/mean excess, duration, magnitude-duration on sensitivity grid | 0.1 m/s remains project tolerance, not legal certification |
| Final nearest-route projection | `final_nearest_route_polyline_projection_m` | Stateful ordered reachable route arc | Stateless segment jumps forbidden |
| Clipped final completion | `clipped_final_route_projection_fraction` | `max_forward_progress/route_length` | Zero denominator becomes typed missing |
| Progress | legacy final projection | max/net forward, completion, goal, backtracking | Traveled distance reported separately |
| Travel efficiency | absent | max forward / traveled distance | No zero-denominator substitution |
| False stop | absent | opportunity-qualified duration/episodes | Missing until exclusion context and thresholds are preregistered |
| Raw scalar-speed jerk | `raw_longitudinal_speed_second_difference_chatter_diagnostic` | Filtered body-acceleration jerk control-smoothness auxiliary | Never occupant comfort or NI |
| Raw `speed*yaw_rate` | `raw_speed_times_heading_rate_lateral_kinematic_diagnostic` | Filtered body lateral acceleration proxy | Never seat/occupant acceleration |
| Single-tick decel | `raw_same_tick_scalar_speed_drop_peak_deceleration_diagnostic` | Filtered signed longitudinal body acceleration | Legacy remains diagnostic only |
| Comfort VDV | absent | `planar_kinematic_vdv_like` | Descriptive planar proxy, explicitly not ISO VDV |
| ISO 2631 / SAE J2834 | not assessed | remains not assessed | Seat/vertical/transfer/frequency weighting are missing |
| Legacy stage latency | controlled AutoDL benchmark | target batch8 pool/atoms/context/selector/end-to-end stages | New target architecture requires new nonholdout instrumentation |
| 100 ms latency | architectural reference | `hypothetical_10Hz_budget` sensitivity | Not a production deadline or readiness certification |
| Legacy component all-gate | immutable historical prereg result | future vector hard-safety/guardrail/NI topology | No retrospective claim transfer |

## Invariants

- Old corrected evaluation and Evaluation v2 artifacts remain sealed and
  unchanged.
- The old `honest_no_claim_under_frozen_preregistered_all_gate` decision
  remains historical truth.
- No new endpoint inherits the old SafetyCost weights, thresholds,
  multiplicity, or claim authorization.
- Selector training/weights and final evaluation are scientifically decoupled.
- A future same-ego batch8 experiment must preregister endpoint applicability,
  margins, multiplicity, and missing/failure treatment before outcome access.
