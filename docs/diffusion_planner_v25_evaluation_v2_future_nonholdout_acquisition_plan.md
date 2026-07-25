# V25 Evaluation v2 Evidence Gaps and Minimum Future Nonholdout Acquisition

This plan is prospective only. It does not authorize new Fresh execution,
retraining, deployment, or a claim on the sealed B4 holdout. Any confirmatory
study must first preregister endpoints, thresholds, multiplicity, hard gates,
sample size, exclusions, and the claim rule on evidence that is not the sealed
B4 denominator. The preserved B4 decision is
`honest_no_claim_under_frozen_preregistered_all_gate`.

| Evidence gap | Minimum new nonholdout evidence | Required binding and validation | Why sealed B4 is insufficient |
|---|---|---|---|
| Collision severity | Time-synchronized physical contact state, relative velocity at contact, delta-v or impulse, actor mass/dynamics, and a qualified collision model. | Sensor/simulator qualification, calibration, coordinate/time provenance, contact identity, and per-event uncertainty. | B4 supports geometric overlap only. A kinematic relative-speed proxy is not severity. |
| PET | Frozen conflict-zone geometry and identity plus ego and counterpart entry/exit passage times. | Same coordinate frame, monotonic clock, conflict-zone version SHA, actor identity continuity, and ambiguity rules. | Clearance/TTC/DRAC do not reconstruct post-encroachment time. |
| Candidate0 dynamic actors, if equivalence is not complete | Primary-evaluation actor pose, heading, dimensions, and velocity at every tick, or a prospectively sealed equivalence receipt. | Exact input/action/trajectory/ego/source equivalence and receipt hashes before outcome use. | A supplementary diagnostic replay cannot be spliced into a paired endpoint without exact equivalence. |
| Full road containment where map geometry is absent or ambiguous | Execution-time drivable polygon union, vehicle footprint dimensions/reference, and geometry tolerance. | Map/version SHA, lanelet topology, polygon validity, projection, and run-config cross-link. | Five-point coverage is not full-footprint containment. |
| Unique ordered-route progress | Ordered route polyline/lanelet arc, adjacency, spawn/goal config, and per-tick feasible-transition evidence. | Route SHA, segment identity, travel-bound preregistration, tie/ambiguity handling, and native goal literal binding. | Stateless nearest projection can jump between nearby parallel, self-near, or forked segments. |
| Occupant/seat comfort and ISO/SAE assessment | Multi-axis acceleration at relevant body-contact points, including vertical response, suitable sampling, seat/suspension transfer, orientation, and human exposure context. | Calibrated transducers, mounting and bandwidth record, filtering/frequency weighting, duration, and a prospectively selected standard method. | Planar vehicle-body kinematics omit seat, occupant, vertical, roll, pitch, and transfer behavior. |
| Production real-time behavior | Controlled warm-up, representative concurrent load, scheduler/deadline tracing, hardware/software configuration, repeated cold/hot runs, and failure policy. | Environment image SHA, clock validation, load generator, deadline definition, dropped-work accounting, and tail-latency protocol. | AutoDL `perf_counter_ns` stage timings are controlled-benchmark measurements only. |
| Industrial or regulatory safety | Qualified sensing/dynamics/environment evidence across a prospectively bounded ODD and applicable test procedures. | Traceable requirements, scenario coverage, uncertainty, independent verification, and relevant authority/version. | B4 is a fixed simulation benchmark, not a type-approval or real-road validation program. |

## Minimum prospective decision package

Before acquiring confirmatory data, freeze:

1. Exact endpoint formulas, units, opportunity denominators, missing-data rules,
   and geometry tolerances.
2. Primary and secondary endpoints, directionality, scientifically justified
   thresholds, multiplicity control, NI/superiority margins, and hard-gate
   conjunction.
3. Sampling frame, independent unit, cluster definition, sample size/power,
   exclusions, and failure accounting.
4. Immutable model, fixed DP K=8, identity/protocol/plan, map/route/actor
   provenance, and data-access controls.
5. Independent reviewer implementation and the promotion/deployment boundary.

The current v2 descriptive grids are project coverage summaries only and must
not be silently promoted into industrial or confirmatory thresholds.
