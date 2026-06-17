# DP-CAMP Benders-Style Formalization

This note records the mathematical contract for carrying CAMP's
Trajectron++-era generalized Benders / cutting-plane logic into the fixed
Tier4 Diffusion Planner simulator without claiming more than the current
integration can prove.

It is a formalization milestone only. It does not modify Diffusion Planner,
train CAMP, change the online selector, run formal seeds, or authorize a new
12/36-run matrix.

## Scope

Authoritative integration state at the time of this note:

- CAMP local/GitHub/AutoDL commit:
  `8ae0950c2e9f99fc7daf31c888795b6707060a6c`.
- Diffusion Planner commit:
  `7a1d33da277a1992ec474b5383a0c963c72e04e4`.
- Current CAMP baseline: `redstopfloor05`.
- Formal seeds `11/12/13` remain frozen.

The target is not classical LP-dual Benders. The target is the same proof
shape used by the existing CAMP code: a finite maximum of affine risk-response
functions, exposed to a convex master through active affine cuts. This is
generalized Benders-style constraint generation / cutting-plane optimization.

## Old Trajectron++ CAMP Object

The paper-consistent Trajectron++ CAMP path uses:

- a frozen Trajectron++ encoder / sampler;
- a per-scene embedding `phi_i`;
- a finite candidate pool `Y_i = {y_ik}`;
- normalized nonnegative atom vectors `A_ik`;
- a hard feasibility mask;
- a scene-conditioned map `w_i = Theta [phi_i; 1]` constrained to the simplex;
- a CVaR outer master with regularization.

In `scripts/train/train_camp_select.py`, the Benders-style loop computes
current simplex weights, scores candidates by `A_ik^T w_i`, finds the active
worst candidate, and adds a cut whose gradient is the active atom vector.
`camp_core/camp_core/outer_master/parametric_cvxpy_master.py` then solves a
CVXPY master with simplex constraints, CVaR epigraph variables, and the
accumulated cuts.

For each scene `i`, the risk-response function has the finite-max form

```text
f_i(w_i) = max_{k in F_i} A_ik^T w_i.
```

Because each `A_ik^T w_i` is affine in `w_i`, `f_i` is convex. If
`k* in argmax_k A_ik^T w0`, then `A_i,k*` is a subgradient of `f_i` at `w0`,
and the globally valid supporting cut is

```text
theta_i >= f_i(w0) + A_i,k*^T (w_i - w0).
```

This is the proof object behind the old CAMP Benders-style training claim. It
does not require Trajectron++ itself to be a convex optimization problem; the
convex object is the finite candidate risk-response function after candidate
generation and atom evaluation are fixed.

## Current DP-CAMP Object

The current DP integration has a different data source but can use the same
finite-candidate proof shape.

At each current tick / training record `i`, Diffusion Planner has already
produced a fixed finite candidate set:

```text
Y_i = {y_i1, ..., y_iK}.
```

The following are fixed constants for the record before CAMP scoring:

- the DP candidate trajectories;
- route/map/current-state context;
- DP reward/context feasibility flags;
- candidate progress and reward diagnostics;
- CAMP atom vectors and normalization scales;
- offline outcome labels when training.

The online selector computes normalized nonnegative atom vectors

```text
a_ik in R_+^R
```

for the fixed candidates and scores them as

```text
s_ik(w) = a_ik^T w.
```

The deployed static selector uses a simplex vector `w`; a future theta-mode
selector may use `w_i = Theta [phi_i; 1]` if a compatible DP scene embedding is
trained and audited. In either case, for fixed atoms the score is affine in the
master variable.

The deployed online selection rule is

```text
k_selected in argmin_{k in F_i} a_ik^T w,
```

with fail-closed fallback behavior when `F_i` is empty. The fallback path is an
online engineering policy; it is not part of the convex training master unless
trained as a separately scoped finite-candidate problem.

## DP Risk-Response Subproblem

For robust DP-CAMP training, offline outcome labels identify an oracle
candidate

```text
o_i in argmax_{k in F_i} outcome_ik
```

and nonnegative margins

```text
m_ik = clip(margin_scale * (outcome_i,o_i - outcome_ik), 0, margin_clip).
```

The DP-specific risk-response subproblem is the finite oracle

```text
find k_i*(w) in argmax_{k in F_i}
    m_ik + (a_i,o_i - a_ik)^T w.
```

Define the per-record violation function

```text
q_i(w) = max(0, max_{k in F_i} m_ik + (a_i,o_i - a_ik)^T w).
```

This is a finite maximum of affine functions and zero, so it is convex in
`w`. The active candidate `k_i*(w0)` gives the globally valid cut

```text
ell_i >= m_i,k* + (a_i,o_i - a_i,k*)^T w.
```

Equivalently, in BendersCut notation at anchor `w0`:

```text
value    = m_i,k* + (a_i,o_i - a_i,k*)^T w0
gradient = a_i,o_i - a_i,k*
ell_i   >= value + gradient^T (w - w0).
```

The current `camp_core/camp_core/outer_master/robust_margin_master.py` uses
this exact finite-candidate cutting-plane structure, although it stores active
candidate indices rather than the older `BendersCut` objects. The solver
repeatedly solves a master over the active candidate constraints, recomputes
the true worst candidate over all logged candidates, and adds missing active
constraints until the master gap is within tolerance.

## Master Problem

For static DP-CAMP weights, the master variables are:

```text
w in R_+^R
ell_i >= 0 for each training record
eta, e_i >= 0 for CVaR when risk_type = cvar
```

with constraints:

```text
sum_r w_r = 1
w_r >= lower_r
ell_i >= m_ik + (a_i,o_i - a_ik)^T w    for active cuts k
e_i >= ell_i - eta
```

and objective:

```text
minimize eta + (1 / ((1 - alpha) N)) sum_i e_i
         + lambda ||w - uniform||_2^2.
```

For theta mode, `w_i` is affine in `Theta` for each record and constrained to
the simplex per record. The same finite affine cuts apply with `w_i` in place
of the static `w`, and the L2 regularizer acts on `Theta`.

The feasible set is nonempty when:

- the atom dimension is positive;
- every training record has at least one finite feasible oracle candidate;
- lower bounds are finite, nonnegative, and sum to at most one;
- feature values are finite in theta mode.

The loss variables can always be chosen large enough to satisfy the finite
cuts, and the simplex is nonempty under the lower-bound condition.

## What Is Not in the Subproblem

The following are not optimization variables in the DP-CAMP Benders-style
subproblem:

- the Diffusion Planner neural diffusion sampler;
- latent sampling controls;
- Savitzky-Golay smoothing;
- `postprocess_reference`;
- PerfectTracker commands or state transitions;
- simulator closed-loop future states;
- route/lane/traffic-light map geometry;
- DP model weights or CAMP atom schema.

These components may produce fixed candidates, fixed diagnostics, feasibility
flags, or offline labels. Once recorded for a tick, those quantities are
constants in the finite-candidate master. They do not provide trajectory
coordinate convexity, classical recourse dual variables, or strong-duality
Benders cuts.

## Naming Boundary

The valid claim for the current DP-CAMP training object is:

```text
finite-candidate generalized Benders-style cutting-plane optimization
```

or:

```text
finite-candidate convex robust-margin master with active risk-response cuts
```

The invalid claims are:

- classical LP-dual Benders decomposition;
- global convexity over DP trajectory coordinates;
- Benders cuts generated by Diffusion Planner, the reward scorer, the
  postprocessor, the tracker, or the closed-loop simulator;
- proof transfer from Trajectron++ to DP without the fixed-candidate
  reformulation above.

The classical LP-dual Benders label would require a separately defined convex
recourse subproblem, strong duality, and cuts derived from the recourse dual.
That object is not present in the current DP simulator integration.

## Integration Implications

1. Existing online DP-CAMP selection is mathematically compatible with the
   formalization whenever the candidate set, atoms, scales, feasibility mask,
   and weights are fixed before scoring.
2. The current `redstopfloor05` checkpoint should be audited against this
   contract before any new training or matrix run: schema, atom names,
   nonnegative normalization, lower bounds, CVaR/simplex/L2 settings,
   convergence gap, active cuts, and full epigraph consistency.
3. Shadow diagnostics and transformed candidates are outside the formalized
   master unless they are turned into an explicit fixed finite candidate set
   with fixed atoms and a declared feasibility rule before CAMP scoring.
4. A future DP theta-mode checkpoint can reuse the same proof shape only after
   a compatible DP scene embedding and per-record simplex constraints are
   trained and audited.
5. No formal seeds or industrial acceptance matrix should be run from this
   document alone. The next admissible step is the read-only `redstopfloor05`
   asset audit under this contract.

## Code Anchors

- Old CAMP training loop:
  `scripts/train/train_camp_select.py`.
- Old parametric CVXPY master:
  `camp_core/camp_core/outer_master/parametric_cvxpy_master.py`.
- Benders cut data structure:
  `camp_core/camp_core/outer_master/benders_master.py`.
- DP selector and atom schema:
  `camp_core/camp_core/integrations/diffusion_planner.py`.
- DP robust-margin cutting-plane master:
  `camp_core/camp_core/outer_master/robust_margin_master.py`.
- DP robust CAMP training entry point:
  `scripts/integrations/train_diffusion_planner_robust_camp.py`.
