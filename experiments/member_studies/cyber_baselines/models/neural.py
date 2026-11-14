"""Neural backbone forecasters for Cyber benchmark (Issue #95).

Implements 5 neural backbones:
1. MLP/FCNN
2. GRU (Report 1 canonical backbone)
3. LSTM
4. TCN (Temporal Convolutional Network)
5. TimeXer (Endogenous-exogenous cross-attention backbone)
"""

from __future__ import annotations

import torch
from torch import Tensor, nn


def validate_input_tensors(x_hist: Tensor, c_future: Tensor) -> None:
    """Validate shape invariants: [B, 24, 7] and [B, 24, 5]."""
    if x_hist.ndim != 3 or x_hist.shape[1:] != (24, 7):
        raise ValueError(f"x_hist must have shape [B, 24, 7], got {x_hist.shape}")
    if c_future.ndim != 3 or c_future.shape[1:] != (24, 5):
        raise ValueError(f"c_future must have shape [B, 24, 5], got {c_future.shape}")
    if x_hist.shape[0] != c_future.shape[0]:
        raise ValueError("Batch sizes of x_hist and c_future do not match")


class MLPForecaster(nn.Module):
    """Multi-Layer Perceptron / FCNN baseline.

    Flattens 24x7 x_hist and 24x5 c_future into 288 features,
    projects through 2 hidden layers with ReLU, and applies Softplus.
    """

    def __init__(self, hidden_dim1: int = 128, hidden_dim2: int = 64) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(24 * 7, hidden_dim1),
            nn.ReLU(),
            nn.Linear(hidden_dim1, hidden_dim2),
            nn.ReLU(),
        )
        self.head = nn.Sequential(
            nn.Linear(hidden_dim2 + 24 * 5, 64),
            nn.ReLU(),
            nn.Linear(64, 24),
            nn.Softplus(),
        )

    def encode(self, x_hist: Tensor) -> Tensor:
        return self.encoder(x_hist.flatten(1))

    def forward(self, x_hist: Tensor, c_future: Tensor) -> Tensor:
        validate_input_tensors(x_hist, c_future)
        z = self.encode(x_hist)
        return self.head(torch.cat((z, c_future.flatten(1)), dim=1))


class GRUForecaster(nn.Module):
    """Canonical Report 1 ForecastGRU backbone.

    2-layer GRU encoder (hidden=64) + calendar-conditioned MLP head + Softplus.
    """

    def __init__(self, hidden_dim: int = 64, head_width: int = 64) -> None:
        super().__init__()
        self.encoder = nn.GRU(7, hidden_dim, num_layers=2, batch_first=True, dropout=0.0)
        self.head = nn.Sequential(
            nn.Linear(hidden_dim + 24 * 5, head_width),
            nn.ReLU(),
            nn.Linear(head_width, 24),
            nn.Softplus(),
        )

    def encode(self, x_hist: Tensor) -> Tensor:
        _, hidden = self.encoder(x_hist)
        return hidden[-1]

    def forward(self, x_hist: Tensor, c_future: Tensor) -> Tensor:
        validate_input_tensors(x_hist, c_future)
        z = self.encode(x_hist)
        return self.head(torch.cat((z, c_future.flatten(1)), dim=1))


class LSTMForecaster(nn.Module):
    """2-layer LSTM encoder + calendar-conditioned MLP head + Softplus."""

    def __init__(self, hidden_dim: int = 64, head_width: int = 64) -> None:
        super().__init__()
        self.encoder = nn.LSTM(7, hidden_dim, num_layers=2, batch_first=True, dropout=0.0)
        self.head = nn.Sequential(
            nn.Linear(hidden_dim + 24 * 5, head_width),
            nn.ReLU(),
            nn.Linear(head_width, 24),
            nn.Softplus(),
        )

    def encode(self, x_hist: Tensor) -> Tensor:
        _, (hidden, _) = self.encoder(x_hist)
        return hidden[-1]

    def forward(self, x_hist: Tensor, c_future: Tensor) -> Tensor:
        validate_input_tensors(x_hist, c_future)
        z = self.encode(x_hist)
        return self.head(torch.cat((z, c_future.flatten(1)), dim=1))


class Chomp1d(nn.Module):
    """Truncates future padding for causal convolutions."""

    def __init__(self, chomp_size: int) -> None:
        super().__init__()
        self.chomp_size = chomp_size

    def forward(self, x: Tensor) -> Tensor:
        return x[:, :, : -self.chomp_size]


class TemporalBlock(nn.Module):
    """Dilated causal convolution residual block."""

    def __init__(
        self, in_channels: int, out_channels: int, kernel_size: int, dilation: int
    ) -> None:
        super().__init__()
        padding = (kernel_size - 1) * dilation
        self.conv1 = nn.Conv1d(
            in_channels, out_channels, kernel_size, padding=padding, dilation=dilation
        )
        self.chomp1 = Chomp1d(padding)
        self.relu1 = nn.ReLU()
        self.conv2 = nn.Conv1d(
            out_channels, out_channels, kernel_size, padding=padding, dilation=dilation
        )
        self.chomp2 = Chomp1d(padding)
        self.relu2 = nn.ReLU()

        self.downsample = (
            nn.Conv1d(in_channels, out_channels, 1) if in_channels != out_channels else None
        )
        self.relu = nn.ReLU()

    def forward(self, x: Tensor) -> Tensor:
        out = self.relu1(self.chomp1(self.conv1(x)))
        out = self.relu2(self.chomp2(self.conv2(out)))
        res = x if self.downsample is None else self.downsample(x)
        return self.relu(out + res)


class TCNForecaster(nn.Module):
    """Temporal Convolutional Network backbone.

    3 residual blocks with dilations 1, 2, 4 (receptive field = 29 > 24).
    Extracts final temporal step output as latent vector [B, 64].
    """

    def __init__(self, hidden_dim: int = 64, head_width: int = 64) -> None:
        super().__init__()
        self.network = nn.Sequential(
            TemporalBlock(7, hidden_dim, kernel_size=3, dilation=1),
            TemporalBlock(hidden_dim, hidden_dim, kernel_size=3, dilation=2),
            TemporalBlock(hidden_dim, hidden_dim, kernel_size=3, dilation=4),
        )
        self.head = nn.Sequential(
            nn.Linear(hidden_dim + 24 * 5, head_width),
            nn.ReLU(),
            nn.Linear(head_width, 24),
            nn.Softplus(),
        )

    def encode(self, x_hist: Tensor) -> Tensor:
        # Transpose from [B, T, C] to [B, C, T]
        x_trans = x_hist.transpose(1, 2)
        out = self.network(x_trans)  # [B, hidden_dim, 24]
        return out[:, :, -1]  # Last time step [B, 64]

    def forward(self, x_hist: Tensor, c_future: Tensor) -> Tensor:
        validate_input_tensors(x_hist, c_future)
        z = self.encode(x_hist)
        return self.head(torch.cat((z, c_future.flatten(1)), dim=1))


class TimeXerForecaster(nn.Module):
    """TimeXer backbone with endogenous-exogenous cross-attention.

    Projects endogenous series (24x7) and exogenous calendar (24x5) into
    embedding space D=64, processes through self-attention and cross-attention,
    and maps to 24 future outputs with Softplus.
    """

    def __init__(self, embed_dim: int = 64, num_heads: int = 4, head_width: int = 64) -> None:
        super().__init__()
        self.embed_dim = embed_dim
        self.endo_proj = nn.Linear(7, embed_dim)
        self.exo_proj = nn.Linear(5, embed_dim)

        self.pos_emb = nn.Parameter(torch.randn(1, 24, embed_dim) * 0.02)

        # Endogenous self-attention
        self.self_attn = nn.MultiheadAttention(embed_dim, num_heads, batch_first=True)
        self.norm1 = nn.LayerNorm(embed_dim)

        # Cross-attention: Endogenous queries Exogenous
        self.cross_attn = nn.MultiheadAttention(embed_dim, num_heads, batch_first=True)
        self.norm2 = nn.LayerNorm(embed_dim)

        # Feed-forward network
        self.ffn = nn.Sequential(
            nn.Linear(embed_dim, embed_dim * 2),
            nn.ReLU(),
            nn.Linear(embed_dim * 2, embed_dim),
        )
        self.norm3 = nn.LayerNorm(embed_dim)

        self.head = nn.Sequential(
            nn.Linear(embed_dim + 24 * 5, head_width),
            nn.ReLU(),
            nn.Linear(head_width, 24),
            nn.Softplus(),
        )

    def encode(self, x_hist: Tensor) -> Tensor:
        B, T, _ = x_hist.shape
        endo = self.endo_proj(x_hist) + self.pos_emb[:, :T, :]
        # Self-attention
        attn_out, _ = self.self_attn(endo, endo, endo)
        endo = self.norm1(endo + attn_out)
        # Global mean pool across temporal steps
        return endo.mean(dim=1)  # [B, 64]

    def forward(self, x_hist: Tensor, c_future: Tensor) -> Tensor:
        validate_input_tensors(x_hist, c_future)
        B, T, _ = x_hist.shape
        endo = self.endo_proj(x_hist) + self.pos_emb[:, :T, :]
        exo = self.exo_proj(c_future) + self.pos_emb[:, :T, :]

        # 1. Endogenous self-attention
        attn_out, _ = self.self_attn(endo, endo, endo)
        endo = self.norm1(endo + attn_out)

        # 2. Exogenous cross-attention
        cross_out, _ = self.cross_attn(query=endo, key=exo, value=exo)
        endo = self.norm2(endo + cross_out)

        # 3. FFN
        ffn_out = self.ffn(endo)
        endo = self.norm3(endo + ffn_out)

        # Latent vector pooled
        z = endo.mean(dim=1)
        return self.head(torch.cat((z, c_future.flatten(1)), dim=1))
