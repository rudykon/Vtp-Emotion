"""MER-PS V3: Simplified model — smaller, more regularized, no over-engineering."""

from __future__ import annotations

import math

import torch
from torch import nn
import torch.nn.functional as F


# ── Graph utilities (from baseline) ──────────────────────────────

def normalize_adjacency(adjacency: torch.Tensor, symmetric: bool = True) -> torch.Tensor:
    adjacency = F.relu(adjacency)
    if symmetric:
        adjacency = adjacency + adjacency.transpose(0, 1)
    adjacency = adjacency + torch.eye(adjacency.size(0), device=adjacency.device, dtype=adjacency.dtype)
    degree = adjacency.sum(dim=1).clamp_min(1e-6)
    inv_sqrt = degree.rsqrt()
    return inv_sqrt[:, None] * adjacency * inv_sqrt[None, :]


def chebyshev_supports(adjacency: torch.Tensor, order: int) -> list[torch.Tensor]:
    if order < 1:
        raise ValueError("Chebyshev order must be >= 1")
    supports = [torch.eye(adjacency.size(0), device=adjacency.device, dtype=adjacency.dtype)]
    if order == 1:
        return supports
    supports.append(adjacency)
    for _ in range(2, order):
        supports.append(torch.matmul(supports[-1], adjacency))
    return supports


class GraphConvolution(nn.Module):
    def __init__(self, in_features: int, out_features: int):
        super().__init__()
        self.weight = nn.Parameter(torch.empty(in_features, out_features))
        self.bias = nn.Parameter(torch.zeros(out_features))
        nn.init.xavier_uniform_(self.weight)

    def forward(self, x: torch.Tensor, support: torch.Tensor) -> torch.Tensor:
        propagated = torch.einsum("nm,bmf->bnf", support, x)
        return torch.matmul(propagated, self.weight) + self.bias


# ── Encoders ─────────────────────────────────────────────────────

class ChebGraphEncoder(nn.Module):
    """Multi-scale Chebyshev GCN encoder."""
    def __init__(self, num_nodes: int, in_features: int, hidden_dim: int,
                 cheb_orders: tuple[int, ...] = (1, 2, 3), dropout: float = 0.3):
        super().__init__()
        self.num_nodes = num_nodes
        self.cheb_orders = cheb_orders
        self.input_norm = nn.BatchNorm1d(in_features)
        self.adjacency = nn.Parameter(torch.empty(num_nodes, num_nodes))
        nn.init.xavier_uniform_(self.adjacency)

        # One conv per Chebyshev order
        self.convs = nn.ModuleList([
            nn.ModuleList([GraphConvolution(in_features, hidden_dim) for _ in cheb_orders])
        ])
        # Actually: each order gets its own GraphConvolution, outputs summed
        self.convs_k = nn.ModuleList([
            GraphConvolution(in_features, hidden_dim) for _ in cheb_orders
        ])
        self.merge = nn.Linear(len(cheb_orders) * hidden_dim, hidden_dim)
        self.output_norm = nn.LayerNorm(hidden_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: [B, nodes, features]
        x = self.input_norm(x.transpose(1, 2)).transpose(1, 2)
        adjacency = normalize_adjacency(self.adjacency)
        supports = chebyshev_supports(adjacency, max(self.cheb_orders))

        branch_outputs = []
        for k_idx, k in enumerate(self.cheb_orders):
            # Use k-th Chebyshev support
            support = supports[k - 1] if k - 1 < len(supports) else supports[-1]
            out = self.convs_k[k_idx](x, support)
            out = F.gelu(out)
            branch_outputs.append(out)

        out = torch.cat(branch_outputs, dim=-1)  # [B, N, 3*hidden]
        out = self.merge(out)  # [B, N, hidden]
        out = F.gelu(out)
        out = self.output_norm(out)
        return self.dropout(out)


class CrossModalBlock(nn.Module):
    """Cross-attention between EEG and fNIRS token sequences."""
    def __init__(self, hidden_dim: int, heads: int = 4, dropout: float = 0.3):
        super().__init__()
        self.attn = nn.MultiheadAttention(embed_dim=hidden_dim, num_heads=heads,
                                          dropout=dropout, batch_first=True)
        self.norm1 = nn.LayerNorm(hidden_dim)
        self.ffn = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim * 4),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 4, hidden_dim),
        )
        self.norm2 = nn.LayerNorm(hidden_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, query: torch.Tensor, context: torch.Tensor) -> torch.Tensor:
        attended, _ = self.attn(query=query, key=context, value=context, need_weights=False)
        x = self.norm1(query + self.dropout(attended))
        return self.norm2(x + self.dropout(self.ffn(x)))


class ContrastiveAlignmentLoss(nn.Module):
    def __init__(self, temperature: float = 0.5):
        super().__init__()
        self.temperature = temperature

    def forward(self, eeg_emb: torch.Tensor, fnirs_emb: torch.Tensor) -> torch.Tensor:
        bs = eeg_emb.size(0)
        if bs < 2:
            return eeg_emb.new_zeros(())
        z_e = F.normalize(eeg_emb, dim=1)
        z_f = F.normalize(fnirs_emb, dim=1)
        logits = torch.matmul(z_e, z_f.t()) / self.temperature
        labels = torch.arange(bs, device=eeg_emb.device)
        return 0.5 * (F.cross_entropy(logits, labels) + F.cross_entropy(logits.t(), labels))


# ── Main Model ────────────────────────────────────────────────────

class MERPSNetV3(nn.Module):
    """Simplified EEG-fNIRS fusion for MER-PS regression.

    Design choices:
      - No temporal encoder because features already include context
      - No FiLM/subject embedding to reduce overfitting
      - Single CrossModalBlock (not stacked 2)
      - Smaller: hidden_dim=64, dropout=0.5
    """

    def __init__(
        self,
        eeg_nodes: int = 64,
        eeg_features: int = 45,
        fnirs_nodes: int = 51,
        fnirs_features: int = 90,
        output_dim: int = 2,
        hidden_dim: int = 64,
        cheb_orders: tuple[int, ...] = (1, 2, 3),
        heads: int = 4,
        dropout: float = 0.5,
        projection_dim: int = 32,
        temperature: float = 0.5,
    ):
        super().__init__()
        if hidden_dim % heads != 0:
            raise ValueError(f"hidden_dim ({hidden_dim}) must be divisible by heads ({heads})")

        self.eeg_encoder = ChebGraphEncoder(eeg_nodes, eeg_features, hidden_dim, cheb_orders, dropout)
        self.fnirs_encoder = ChebGraphEncoder(fnirs_nodes, fnirs_features, hidden_dim, cheb_orders, dropout)

        self.eeg_to_fnirs = CrossModalBlock(hidden_dim, heads, dropout)
        self.fnirs_to_eeg = CrossModalBlock(hidden_dim, heads, dropout)

        self.eeg_projector = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim), nn.GELU(),
            nn.Linear(hidden_dim, projection_dim),
        )
        self.fnirs_projector = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim), nn.GELU(),
            nn.Linear(hidden_dim, projection_dim),
        )
        self.alignment_loss = ContrastiveAlignmentLoss(temperature)

        # Pooled: mean+max of (eeg_graph, fnirs_graph, eeg_cross, fnirs_cross) = 8*hidden_dim
        pooled_dim = hidden_dim * 8
        self.regressor = nn.Sequential(
            nn.LayerNorm(pooled_dim),
            nn.Linear(pooled_dim, hidden_dim * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, output_dim),
        )
        self._reset_parameters()

    def _reset_parameters(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.kaiming_uniform_(m.weight, a=math.sqrt(5))
                if m.bias is not None:
                    fan_in, _ = nn.init._calculate_fan_in_and_fan_out(m.weight)
                    bound = 1 / math.sqrt(fan_in) if fan_in > 0 else 0
                    nn.init.uniform_(m.bias, -bound, bound)

    def forward(self, eeg: torch.Tensor, fnirs: torch.Tensor,
                subject_ids: torch.Tensor | None = None) -> tuple[torch.Tensor, torch.Tensor]:
        # Encode
        eeg_graph = self.eeg_encoder(eeg)       # [B, 64, hidden]
        fnirs_graph = self.fnirs_encoder(fnirs)  # [B, 51, hidden]

        # Global embeddings for contrastive loss
        eeg_global = eeg_graph.mean(dim=1)
        fnirs_global = fnirs_graph.mean(dim=1)
        contrastive_loss = self.alignment_loss(
            self.eeg_projector(eeg_global),
            self.fnirs_projector(fnirs_global),
        )

        # Cross-modal
        eeg_cross = self.eeg_to_fnirs(eeg_graph, fnirs_graph)
        fnirs_cross = self.fnirs_to_eeg(fnirs_graph, eeg_graph)

        # Pool (same as baseline: mean + max for 4 token sets)
        pooled = torch.cat([
            eeg_graph.mean(dim=1), eeg_graph.amax(dim=1),
            fnirs_graph.mean(dim=1), fnirs_graph.amax(dim=1),
            eeg_cross.mean(dim=1), eeg_cross.amax(dim=1),
            fnirs_cross.mean(dim=1), fnirs_cross.amax(dim=1),
        ], dim=1)

        prediction = torch.sigmoid(self.regressor(pooled))
        return prediction, contrastive_loss
