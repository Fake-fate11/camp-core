from typing import Optional, Tuple

import numpy as np
import torch
from torch import nn

from camp_core.integrations.diffusion_planner_v25_context import (
    PHI_DIMENSION,
    validate_column_simplex_theta,
)


class LinearMappingHead(nn.Module):
    """Linear mapping from embeddings to weights (raw logits).

    Unlike Softmax-based heads, this head returns w = Theta * phi
    where Theta is the learnable parameter matrix. 
    
    The constraints w >= 0 and sum(w) = 1 are NOT enforced here,
    but must be enforced by the Master optimization problem (CVXPY) 
    or by the downstream logic.

    Args:
        embedding_dim: Dimension of input intermediate features phi(xi).
        num_atoms: Dimension of output weight vector w.
        use_bias: Whether to include a bias term (affine map).
    """

    def __init__(
        self,
        embedding_dim: int,
        num_atoms: int,
        use_bias: bool = False,
    ) -> None:
        super().__init__()
        self.embedding_dim = embedding_dim
        self.num_atoms = num_atoms
        # Theta is represented by the weight matrix of a Linear layer
        self.linear = nn.Linear(embedding_dim, num_atoms, bias=use_bias)

    def forward(self, embeddings: torch.Tensor) -> torch.Tensor:
        """Map embeddings of shape (B, D) to raw weights of shape (B, K)."""
        if embeddings.dim() != 2:
            raise ValueError(
                f"Expected embeddings to have shape (B, D), got {embeddings.shape}"
            )
        if embeddings.size(1) != self.embedding_dim:
            raise ValueError(
                f"Expected embedding_dim={self.embedding_dim}, got {embeddings.size(1)}"
            )

        # w = Theta * phi (+ bias)
        weights = self.linear(embeddings)
        return weights

    def extra_repr(self) -> str:
        return f"embedding_dim={self.embedding_dim}, num_atoms={self.num_atoms}, active=Linear(NoSoftmax)"


class ComplementLiftedSimplexHead(nn.Module):
    """Strict V25 linear head with a universal simplex guarantee.

    ``phi`` is the frozen nonnegative 53D complement lift and sums to one.
    Every column of ``Theta`` is independently constrained to the atom simplex.
    Consequently ``w(x) = Theta @ phi(x)`` is a simplex for every admissible
    current-tick context, without a bias, softmax, neural adapter, or runtime
    projection.
    """

    def __init__(
        self,
        *,
        num_atoms: int,
        theta: Optional[np.ndarray] = None,
        trainable: bool = False,
    ) -> None:
        super().__init__()
        if int(num_atoms) < 1:
            raise ValueError("num_atoms must be positive.")
        self.num_atoms = int(num_atoms)
        if theta is None:
            values = np.full(
                (self.num_atoms, PHI_DIMENSION),
                1.0 / self.num_atoms,
                dtype=np.float64,
            )
        else:
            values = validate_column_simplex_theta(
                theta, num_atoms=self.num_atoms
            ).copy()
        tensor = torch.as_tensor(values, dtype=torch.float64)
        if trainable:
            self.theta = nn.Parameter(tensor)
        else:
            self.register_buffer("theta", tensor)

    def forward(self, phi: torch.Tensor) -> torch.Tensor:
        if phi.dim() != 2 or phi.size(1) != PHI_DIMENSION:
            raise ValueError(
                f"Expected phi to have shape (B, {PHI_DIMENSION}), got {phi.shape}"
            )
        if not torch.isfinite(phi).all() or torch.any(phi < -1e-10):
            raise ValueError("phi must be finite and nonnegative.")
        if not torch.allclose(
            phi.sum(dim=1),
            torch.ones(phi.size(0), dtype=phi.dtype, device=phi.device),
            rtol=0.0,
            atol=1e-9,
        ):
            raise ValueError("every phi row must sum to one.")
        theta = self.theta.to(dtype=phi.dtype, device=phi.device)
        if not torch.isfinite(theta).all() or torch.any(theta < -1e-9):
            raise ValueError("every Theta column must be finite and nonnegative.")
        if not torch.allclose(
            theta.sum(dim=0),
            torch.ones(PHI_DIMENSION, dtype=phi.dtype, device=phi.device),
            rtol=0.0,
            atol=1e-8,
        ):
            raise ValueError("every Theta column must sum to one.")
        weights = phi @ theta.T
        if torch.any(weights < -1e-9) or not torch.allclose(
            weights.sum(dim=1),
            torch.ones(phi.size(0), dtype=phi.dtype, device=phi.device),
            rtol=0.0,
            atol=1e-8,
        ):
            raise ValueError("V25 context head violated its simplex guarantee.")
        return weights

    def extra_repr(self) -> str:
        return (
            f"phi_dimension={PHI_DIMENSION}, num_atoms={self.num_atoms}, "
            "active=ColumnSimplexLinear(NoBias,NoSoftmax,NoProjection)"
        )
