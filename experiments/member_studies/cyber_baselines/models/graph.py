"""Basic GCN-LSTM spatial comparator baseline for Cyber benchmark (Issue #95)."""

from __future__ import annotations

from typing import Any

import numpy as np
import torch
from torch import Tensor, nn

from experiments.member_studies.cyber_baselines.models.base import BaseForecaster


class GCNLayer(nn.Module):
    """Graph Convolutional layer: Z = A_norm @ X @ W + b."""

    def __init__(self, in_features: int, out_features: int) -> None:
        super().__init__()
        self.weight = nn.Parameter(torch.FloatTensor(in_features, out_features))
        self.bias = nn.Parameter(torch.FloatTensor(out_features))
        self.reset_parameters()

    def reset_parameters(self) -> None:
        nn.init.xavier_uniform_(self.weight)
        nn.init.zeros_(self.bias)

    def forward(self, x: Tensor, adj_norm: Tensor) -> Tensor:
        # x: [B, N, F_in], adj_norm: [N, N]
        # output: [B, N, F_out]
        support = torch.matmul(x, self.weight)  # [B, N, F_out]
        output = torch.matmul(adj_norm, support) + self.bias
        return output


class GCNLSTMNet(nn.Module):
    """Spatiotemporal architecture combining GCN and LSTM across graph nodes."""

    def __init__(
        self,
        num_nodes: int,
        adj_norm: Tensor,
        in_dim: int = 7,
        gcn_dim: int = 32,
        lstm_dim: int = 64,
        head_width: int = 64,
    ) -> None:
        super().__init__()
        self.num_nodes = num_nodes
        self.register_buffer("adj_norm", adj_norm)

        self.gcn = GCNLayer(in_dim, gcn_dim)
        self.relu = nn.ReLU()
        # LSTM processes sequence across 24 time steps for each node
        self.lstm = nn.LSTM(gcn_dim, lstm_dim, batch_first=True)
        # Node-specific head
        self.head = nn.Sequential(
            nn.Linear(lstm_dim + 24 * 5, head_width),
            nn.ReLU(),
            nn.Linear(head_width, 24),
            nn.Softplus(),
        )

    def forward(self, x_seq: Tensor, c_future: Tensor, node_idx: int) -> Tensor:
        """Forward pass.

        x_seq: [B, 24, N, 7] (temporal sequence of graph node features)
        c_future: [B, 24, 5] (future calendar features for the target node)
        node_idx: index of the target node in {0..N-1}
        Returns: [B, 24] predictions for the target node
        """
        B, T, N, F = x_seq.shape
        # Apply GCN at each time step
        gcn_steps = []
        for t in range(T):
            x_t = x_seq[:, t, :, :]  # [B, N, F]
            z_t = self.relu(self.gcn(x_t, self.adj_norm))  # [B, N, gcn_dim]
            gcn_steps.append(z_t)

        # Stack across time: [B, T, N, gcn_dim]
        gcn_out = torch.stack(gcn_steps, dim=1)

        # Extract sequence for target node: [B, T, gcn_dim]
        node_seq = gcn_out[:, :, node_idx, :]

        # Pass through LSTM
        _, (h_n, _) = self.lstm(node_seq)
        z = h_n[-1]  # [B, lstm_dim]

        # Combine with target future calendar
        combined = torch.cat((z, c_future.flatten(1)), dim=1)
        return self.head(combined)


class BasicGCNLSTM(BaseForecaster):
    """Spatial comparator baseline wrapping GCNLSTMNet."""

    def __init__(
        self,
        node_ids: list[str],
        adj_norm: np.ndarray,
        target_id: str,
        seed: int = 42,
        initial_records: list[dict[str, Any]] | None = None,
    ) -> None:
        self.node_ids = node_ids
        self.target_id = target_id
        self.target_idx = node_ids.index(target_id)
        self.seed = seed

        torch.manual_seed(seed)
        np.random.seed(seed)

        adj_tensor = torch.tensor(adj_norm, dtype=torch.float32)
        self.net = GCNLSTMNet(num_nodes=len(node_ids), adj_norm=adj_tensor)
        self.optimizer = torch.optim.Adam(self.net.parameters(), lr=1e-3)

        # Buffer for recent node histories
        self.recent_x_hist: dict[str, list[list[float]]] = {
            nid: [[0.0] * 7] * 24 for nid in node_ids
        }

        # Train on target initial records if available
        if initial_records:
            self._fit_initial(initial_records)

    @property
    def name(self) -> str:
        return "Basic GCN-LSTM"

    @property
    def param_count(self) -> int:
        return sum(p.numel() for p in self.net.parameters() if p.requires_grad)

    def _fit_initial(self, initial_records: list[dict[str, Any]], epochs: int = 5) -> None:
        self.net.train()
        for _ in range(epochs):
            for rec in initial_records:
                fc = rec.get("forecast", rec)
                x_hist = torch.tensor(fc["x_hist"], dtype=torch.float32).unsqueeze(0)  # [1, 24, 7]
                c_future = torch.tensor(fc["c_future"], dtype=torch.float32).unsqueeze(
                    0
                )  # [1, 24, 5]
                y_label = torch.tensor(rec["y_scaled"], dtype=torch.float32).unsqueeze(0)

                # Broadcast or tile across N nodes for initial target-only training
                x_seq = x_hist.unsqueeze(2).repeat(1, 1, len(self.node_ids), 1)  # [1, 24, N, 7]

                self.optimizer.zero_grad()
                pred = self.net(x_seq, c_future, self.target_idx)
                loss = (pred - y_label).abs().mean()
                loss.backward()
                self.optimizer.step()

    def predict(self, record: dict[str, Any]) -> list[float]:
        self.net.eval()
        with torch.no_grad():
            x_hist = torch.tensor(record["x_hist"], dtype=torch.float32).unsqueeze(0)
            c_future = torch.tensor(record["c_future"], dtype=torch.float32).unsqueeze(0)

            # Sequence across graph nodes: target uses its own x_hist
            x_seq = x_hist.unsqueeze(2).repeat(1, 1, len(self.node_ids), 1)

            pred = self.net(x_seq, c_future, self.target_idx)
            return pred.squeeze(0).cpu().tolist()

    def update(self, record: dict[str, Any], y_scaled: list[float]) -> dict[str, Any]:
        self.net.train()
        x_hist = torch.tensor(record["x_hist"], dtype=torch.float32).unsqueeze(0)
        c_future = torch.tensor(record["c_future"], dtype=torch.float32).unsqueeze(0)
        y_label = torch.tensor(y_scaled, dtype=torch.float32).unsqueeze(0)

        x_seq = x_hist.unsqueeze(2).repeat(1, 1, len(self.node_ids), 1)

        self.optimizer.zero_grad()
        pred = self.net(x_seq, c_future, self.target_idx)
        loss = (pred - y_label).abs().mean()
        loss.backward()
        self.optimizer.step()

        return {"status": "ok", "loss": float(loss.item())}
