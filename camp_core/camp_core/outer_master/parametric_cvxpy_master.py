from __future__ import annotations

import collections
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import cvxpy as cp
import torch
import torch.nn as nn

try:
    import coptpy
except ImportError:
    pass

from camp_core.outer_master.benders_master import BendersCut

@dataclass
class ParametricCVXPYMasterConfig:
    num_atoms: int
    embedding_dim: int
    risk_type: str = "cvar"
    alpha: float = 0.9
    prior_reg_strength: float = 1.0
    offline_anchor_weight: float = 0.0
    device: str = "cpu"
    solver: str = "ECOS"

class ParametricCVXPYMaster:
    def __init__(
        self,
        config: ParametricCVXPYMasterConfig,
        scene_embeddings: np.ndarray, # [M, D] (or tensor, we will handle on CPU)
    ):
        self.cfg = config
        self.num_atoms = config.num_atoms
        self.emb_dim = config.embedding_dim
        
        # Convert embeddings to CPU numpy
        if isinstance(scene_embeddings, torch.Tensor):
            scene_embeddings = scene_embeddings.detach().cpu().numpy()
            
        self.M = len(scene_embeddings)
        self.M_active = self.M
        
        # Augment embeddings with 1 for bias
        self.phi_aug = np.concatenate([scene_embeddings, np.ones((self.M, 1))], axis=1) # [M, D+1]
        
        # CVXPY Variables
        self.Theta = cp.Variable((self.num_atoms, self.emb_dim + 1))
        self.eta = cp.Variable() # Global VaR
        
        self.cuts = collections.defaultdict(list)
        
        # State
        self.theta_value = np.zeros((self.num_atoms, self.emb_dim + 1))
        # Initialize uniform weights
        self.theta_value[:, -1] = 1.0 / self.num_atoms
        self.last_loss = float('inf')

    def add_cut(self, scenario_idx: int, cut: BendersCut):
        self.cuts[scenario_idx].append(cut)

    def _build_problem(self, active_indices: Optional[Sequence[int]] = None, prior_weights: Optional[np.ndarray] = None):
        if active_indices is None:
            active_indices = np.arange(self.M)
        
        M_act = len(active_indices)
        
        # Local slice of context embeddings
        # self.phi_aug is [M, D+1]
        phi_act = self.phi_aug[active_indices, :] # [M_act, D+1]
        
        # Build strict local variables to eliminate the 20000+ unbounded dummy dimensionalities
        Theta = self.Theta # Just reuse the global model parameters
        W_act = Theta @ phi_act.T # [R, M_act]
        
        theta_vars = cp.Variable(M_act)
        s = cp.Variable(M_act, nonneg=True)
        eta = self.eta
        
        constraints = []
        
        # Weight constraints (Simplex per scene)
        constraints.append(W_act >= 0)
        constraints.append(cp.sum(W_act, axis=0) == 1)
        
        # Build Matrix Vectorized Cuts (MASSIVE SPEEDUP + CORRECT INTERCEPT)
        if M_act > 0 and len(self.cuts[active_indices[0]]) > 0:
            num_cuts = len(self.cuts[active_indices[0]])
            for k in range(num_cuts):
                grad_k = np.array([self.cuts[idx][k].gradient for idx in active_indices]).T # [R, M_act]
                val_k = np.array([self.cuts[idx][k].value for idx in active_indices]) # [M_act]
                w_anch_k = np.array([self.cuts[idx][k].w_anchor for idx in active_indices]).T # [R, M_act]
                
                intercepts = val_k - np.sum(grad_k * w_anch_k, axis=0) # [M_act]
                
                constraints.append(theta_vars >= intercepts + cp.sum(cp.multiply(W_act, grad_k), axis=0))
                
        # Vectorized CVaR constraints
        constraints.append(s >= theta_vars - eta)
            
        # Objective
        if self.cfg.risk_type == "cvar":
            risk_obj = eta + (1.0 / ((1.0 - self.cfg.alpha) * M_act)) * cp.sum(s)
        else: # mean
            risk_obj = (1.0 / M_act) * cp.sum(theta_vars)
            
        # Regularization (Bayesian Trust Region / L2)
        reg_obj = 0.0
        if self.cfg.prior_reg_strength > 0:
            reg_obj = self.cfg.prior_reg_strength * cp.sum_squares(Theta)
            
        # Offline Anchor Weight Regularization (Distance from prior on average)
        anchor_obj = 0.0
        if self.cfg.offline_anchor_weight > 0 and prior_weights is not None:
            # W_mean = average of W over all active scenes
            W_mean = cp.sum(W_act, axis=1) / M_act
            anchor_obj = self.cfg.offline_anchor_weight * cp.sum_squares(W_mean - prior_weights)
            
        obj = cp.Minimize(risk_obj + reg_obj + anchor_obj)
        prob = cp.Problem(obj, constraints)
        return prob, risk_obj

    def solve(self, verbose: bool = False, active_indices: Optional[Sequence[int]] = None, prior_weights: Optional[np.ndarray] = None):
        prob, risk_obj = self._build_problem(active_indices, prior_weights)
        
        try:
            solver_mode = getattr(cp, self.cfg.solver.upper())
            
            # Try primary solver with increased iterations if supported
            kwargs = {}
            if self.cfg.solver.upper() == "CLARABEL":
                kwargs["max_iter"] = 1000
            elif self.cfg.solver.upper() == "SCS":
                kwargs["max_iters"] = 5000
                
            prob.solve(solver=solver_mode, verbose=verbose, **kwargs)
            
            # Soft failure fallback
            if prob.status not in [cp.OPTIMAL, cp.OPTIMAL_INACCURATE]:
                print(f"Primary solver {self.cfg.solver.upper()} returned {prob.status}. Triggering ECOS fallback...")
                prob.solve(solver=cp.ECOS, verbose=verbose, max_iters=5000)
                
                if prob.status not in [cp.OPTIMAL, cp.OPTIMAL_INACCURATE]:
                    print(f"ECOS returned {prob.status}. Triggering SCS fallback...")
                    prob.solve(solver=cp.SCS, verbose=verbose, max_iters=10000)
                    
        except AttributeError:
            print(f"Solver {self.cfg.solver} not found in cvxpy. Falling back to ECOS/SCS.")
            try: prob.solve(solver=cp.ECOS, verbose=verbose, max_iters=5000)
            except cp.SolverError: prob.solve(solver=cp.SCS, verbose=verbose, max_iters=10000)
        except cp.SolverError as e:
            if self.cfg.solver.upper() != "SCS":
                try: prob.solve(solver=cp.SCS, verbose=verbose, max_iters=10000)
                except cp.SolverError as e2: return {"status": "error", "error": str(e2)}
            else: return {"status": "error", "error": str(e)}
        
        if prob.status in [cp.OPTIMAL, cp.OPTIMAL_INACCURATE]:
            self.theta_value = self.Theta.value
            self.last_loss = prob.value
            return {
                "status": "optimal",
                "loss": prob.value,
                "risk_loss": risk_obj.value,
                "Theta": self.theta_value
            }
        else:
            return {"status": prob.status}

    def update_head_weights(self, head: nn.Module, theta_value: np.ndarray):
        with torch.no_grad():
            head.linear.weight.copy_(torch.tensor(theta_value[:, :-1], dtype=torch.float32))
            head.linear.bias.copy_(torch.tensor(theta_value[:, -1], dtype=torch.float32))

